import dannce.config as config
from dannce.engine.data import ops
import dannce.engine.inference as inference
from dannce.engine.models.pose2d.sleap import SLEAPUNet
from dannce.run_utils import *
from dannce.engine.logging.logger import setup_logging, get_logger
from dannce.engine.trainer.com_trainer import COMTrainer
from dannce.engine.data.dataset import RAT7MImageDataset
from dannce.run.train_backbone2d import load_data2d_into_mem

import scipy.io as sio

def collate_fn(batch):
    X = torch.stack([item[0] for item in batch], dim=0)
    y = torch.stack([item[1] for item in batch], dim=0)

    return X, y

def train(params):
    params, base_params, shared_args, shared_args_train, shared_args_valid = config.setup_train(params)

    # make the train directory if does not exist
    make_folder("dannce_train_dir", params)

    # setup logger
    setup_logging(params["dannce_train_dir"])
    logger = get_logger("training.log", verbosity=2) 
    
    assert torch.cuda.is_available(), "No available GPU device."
    params["gpu_id"] = [0]
    device = torch.device("cuda")
    logger.info("***Use {} GPU for training.***".format(params["gpu_id"]))

    # fix random seed if specified
    if params["random_seed"] is not None:
        set_random_seed(params["random_seed"])
        logger.info("***Fix random seed as {}***".format(params["random_seed"]))

    model = SLEAPUNet(params["n_channels_in"], params["n_channels_out"])
    if params["train_mode"] == "finetune" and params["dannce_finetune_weights"] is not None:
        print("Loading checkpoint from {}".format(params["dannce_finetune_weights"]))
        state_dict = torch.load(params["dannce_finetune_weights"])["state_dict"]
        ckpt_channel_num = state_dict["output_layer.weight"].shape[0]
        if ckpt_channel_num != params["n_channels_out"]:
            state_dict.pop("output_layer.weight", None)
            state_dict.pop("output_layer.bias", None)
        model.load_state_dict(state_dict, strict=False)

    model_params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.Adam(model_params, lr=params["lr"], eps=1e-7)
    lr_scheduler = None
    if params["lr_scheduler"] is not None:
        lr_scheduler_class = getattr(torch.optim.lr_scheduler, params["lr_scheduler"]["type"])
        lr_scheduler = lr_scheduler_class(optimizer=optimizer, **params["lr_scheduler"]["args"], verbose=True)
        logger.info("Using learning rate scheduler.")

    model = model.to(device)
    logger.info(model)
    logger.info("COMPLETE\n")

    if params["dataset"] == "rat7m":
        dataset_train = RAT7MImageDataset(train=True, downsample=1)
        dataset_valid = RAT7MImageDataset(train=False, downsample=800)
        logger.info("Train: {} samples".format(len(dataset_train)))
        logger.info("Validation: {} samples".format(len(dataset_valid)))

    elif params["dataset"] == "label3d":
        exps = params["exp"]
        num_experiments = len(exps)
        params["experiment"] = {}
        params["return_full2d"] = True
        (
            samples, 
            datadict, datadict_3d, com3d_dict, 
            cameras, camnames,
            total_chunks,
            temporal_chunks
        ) = processing.load_all_exps(params, logger)

        cameras, datadict, params = serve_data_DANNCE.prepend_experiment(
            params, datadict, num_experiments, camnames, cameras
        )

        # Setup additional variables for later use
        n_cams = len(camnames[0])
        dannce_train_dir = params["dannce_train_dir"]
        outmode = "coordinates" if params["expval"] else "3dprob"
        tifdirs = []  # Training from single images not yet supported in this demo

        vid_exps = np.arange(num_experiments)
        # initialize needed videos
        vids = processing.initialize_all_vids(params, datadict, vid_exps, pathonly=True)

        # make train/valid splits
        partition = processing.make_data_splits(
            samples, params, dannce_train_dir, num_experiments, 
            temporal_chunks=temporal_chunks)

        genfunc = generator.MultiviewImageGenerator

        base_params = {
            **base_params,
            "camnames": camnames,
            "vidreaders": vids,
            "chunks": total_chunks,
        }
        spec_params = {
            "channel_combo":  params["channel_combo"],
            "expval": params["expval"],
        }

        valid_params = {**base_params, **spec_params}

        train_gen_params = {
            "list_IDs": partition["train_sampleIDs"],
            "labels": datadict,
            "labels_3d": datadict_3d,
            "camera_params": cameras,
            "clusterIDs": partition["train_sampleIDs"],
            "com3d": com3d_dict,
            "tifdirs": tifdirs
        }
        valid_gen_params = {
            "list_IDs": partition["valid_sampleIDs"],
            "labels": datadict,
            "labels_3d": datadict_3d,
            "camera_params": cameras,
            "clusterIDs": partition["valid_sampleIDs"],
            "com3d": com3d_dict,
            "tifdirs": tifdirs
        }
        train_generator = genfunc(**train_gen_params, **valid_params)
        valid_generator = genfunc(**valid_gen_params, **valid_params)
        
        # load everything into memory
        X_train, y_train = load_data2d_into_mem(params, logger, partition, n_cams, train_generator, train=True, image_size=256)
        X_valid, y_valid = load_data2d_into_mem(params, logger, partition, n_cams, valid_generator, train=False, image_size=256)
    
        dataset_train = dataset.ImageDataset(
            images=X_train,
            labels=y_train,
            num_joints=params["n_channels_out"],
            return_Gaussian=True,
            train=True
        )
        dataset_valid = dataset.ImageDataset(
            images=X_valid,
            labels=y_valid,
            num_joints=params["n_channels_out"],
            return_Gaussian=True,
            train=False
        )
    
    train_dataloader = torch.utils.data.DataLoader(
        dataset_train, batch_size=params["batch_size"], shuffle=True, collate_fn=collate_fn,
        num_workers=8,
    )
    valid_dataloader = torch.utils.data.DataLoader(
        dataset_valid, batch_size=params["batch_size"], shuffle=False, collate_fn=collate_fn,
        num_workers=8
    )

    params["com_train_dir"] = params["dannce_train_dir"]
    # set up trainer
    trainer_class = COMTrainer
    trainer = trainer_class(
        params=params,
        model=model,
        train_dataloader=train_dataloader,
        valid_dataloader=valid_dataloader,
        optimizer=optimizer,
        device=device,
        logger=logger,
        lr_scheduler=lr_scheduler
    )

    trainer.train()

def predict(params):
    os.environ["CUDA_VISIBLE_DEVICES"] = params["gpu_id"]
    make_folder("dannce_predict_dir", params)
    device = "cuda:0"
    params["n_instances"] = 20

    dataset_valid = RAT7MImageDataset(train=False, downsample=1)
    cameras = dataset_valid.cameras
    expname = 5
    cameras = cameras[5]
    for k, cam in cameras.items():
        cammat = ops.camera_matrix(cam["K"], cam["R"], cam["t"])
        cameras[k]["cammat"] = cammat

    print("Initializing Network...")
    model = SLEAPUNet(params["n_channels_in"], params["n_channels_out"])
    model.load_state_dict(torch.load(params["dannce_predict_model"])['state_dict'])
    model.eval()   
    model = model.to(device)

    save_data = {}
    n_cams = len(params["camnames"])
    generator_len = dataset_valid.n_samples // n_cams

    endIdx = np.min(
        [
            params["start_sample"] + params["max_num_samples"],
            generator_len
        ]
    ) if params["max_num_samples"] != "max" else generator_len

    partition = {"valid_sampleIDs": np.arange(params["start_sample"], endIdx)}

    for i in tqdm(range(params["start_sample"], endIdx)):
        
        batch, coms = [], []
        for j in range(n_cams):
            batch.append(dataset_valid[i+j*generator_len][0])
            coms.append(dataset_valid.coms[i+j*generator_len])
        batch = torch.stack(batch, dim=0)
        
        pred = model(batch.to(device))
        pred = pred.detach().cpu().numpy()

        sample_id = partition["valid_sampleIDs"][i]
        save_data[sample_id] = {}
        save_data[sample_id]["triangulation"] = {}    

        for n_cam in range(n_cams):
            save_data[sample_id][params["camnames"][n_cam]] = {
                "COM": np.zeros((20, 2)),
            }
            for n_joint in range(pred.shape[1]):
                ind = (
                    np.array(processing.get_peak_inds(np.squeeze(pred[n_cam, n_joint])))
                )
                # breakpoint()
                ind[0] = (ind[0] - 32) * 8 #4
                ind[1] = (ind[1] - 32) * 8 #4
                ind[0] += coms[n_cam][1]
                ind[1] += coms[n_cam][0]
                ind = ind[::-1]

                # Undistort this COM here.
                pts1 = ind
                pts1 = pts1[np.newaxis, :]
                pts1 = ops.unDistortPoints(
                    pts1,
                    cameras[str(expname)+"_"+params["camnames"][n_cam]]["K"],
                    cameras[str(expname)+"_"+params["camnames"][n_cam]]["RDistort"],
                    cameras[str(expname)+"_"+params["camnames"][n_cam]]["TDistort"],
                    cameras[str(expname)+"_"+params["camnames"][n_cam]]["R"],
                    cameras[str(expname)+"_"+params["camnames"][n_cam]]["t"],
                )

                save_data[sample_id][params["camnames"][n_cam]]["COM"][n_joint] = np.squeeze(pts1)

        def vis():
            import matplotlib
            import matplotlib.pyplot as plt
            matplotlib.use('TkAgg')

            fig = plt.figure(figsize=(10, 10))
            ax = fig.add_subplot(121)
            ax.imshow(batch[0].permute(1, 2, 0).numpy().astype(np.uint8))

            com = np.array(coms[0])
            kpts2d = save_data[sample_id][params["camnames"][0]]["COM"] - com[np.newaxis, :]
            kpts2d = kpts2d + 128
            ax.scatter(kpts2d[:, 0], kpts2d[:, 1])

            ax = fig.add_subplot(122)
            ax.imshow(batch[1].permute(1, 2, 0).numpy().astype(np.uint8))

            com = np.array(coms[1])
            kpts2d = save_data[sample_id][params["camnames"][1]]["COM"] - com[np.newaxis, :]
            kpts2d += 128
            ax.scatter(kpts2d[:, 0], kpts2d[:, 1])

            plt.show(block=True)
            input("Press Enter to continue...")
        
 #       if i == 5:
 #           vis()
 #           breakpoint()

        # triangulation
        save_data[sample_id]["joints"] = np.zeros((20, 3))
        for joint in range(pred.shape[1]):
            for n_cam1 in range(n_cams):
                for n_cam2 in range(n_cam1 + 1, n_cams):
                    pts1 = save_data[sample_id][params["camnames"][n_cam1]]["COM"][joint]
                    pts2 = save_data[sample_id][params["camnames"][n_cam2]]["COM"][joint]
                    pts1 = pts1[np.newaxis, :]
                    pts2 = pts2[np.newaxis, :]
                    
                    test3d = ops.triangulate(
                        pts1,
                        pts2,
                        cameras[str(expname)+"_"+params["camnames"][n_cam1]]["cammat"],
                        cameras[str(expname)+"_"+params["camnames"][n_cam2]]["cammat"],
                    ).squeeze()

                    save_data[sample_id]["triangulation"][
                        "{}_{}".format(
                            params["camnames"][n_cam1], params["camnames"][n_cam2]
                        )
                    ] = test3d

            pairs = [
                v for v in save_data[sample_id]["triangulation"].values() if len(v) == 3
            ]   

            pairs = np.stack(pairs, axis=1)
            final = np.nanmedian(pairs, axis=1).squeeze()
            save_data[sample_id]["joints"][joint] = final
    
    pose3d = np.stack([v["joints"] for k, v in save_data.items()], axis=0) #[N, 3, 20]
    # pose2d = np.
    sio.savemat(
        os.path.join(params["dannce_predict_dir"], "pred{}.mat".format(params["start_sample"])),
        {"pose3d": pose3d},
    )
    return