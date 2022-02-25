"""Dannce module and default parameters"""
# Default parameters, which can be superseded by CL arguments or
# config files
_param_defaults_shared = {
    "immode": "vid",
    "verbose": 1,
    "gpu_id": "0",
    "loss": "mask_nan_keep_loss",
    "start_batch": 0,
    "exp": None,
    "viddir": "videos",
    "io_config": None,
    "crop_height": None,
    "crop_width": None,
    "n_channels_in": None,
    "camnames": None,
    "extension": None,
    "n_views": 6,
    "batch_size": None,
    "epochs": None,
    "vid_dir_flag": None,
    "num_validation_per_exp": None,
    "num_train_per_exp": None,
    "chunks": None,
    "lockfirst": None,
    "load_valid": None,
    "mono": False,
    "augment_hue": False,
    "augment_brightness": False,
    "augment_hue_val": 0.05,
    "augment_bright_val": 0.05,
    "augment_rotation_val": 5,
    "mirror_augmentation": False,
    "right_keypoints": None,
    "left_keypoints": None,
    "drop_landmark": None,
    "raw_im_h": None,
    "raw_im_w": None,
    "mirror": False,
    "max_num_samples": None,
    "n_instances": 1,
    "start_sample": 0,
    "write_npy": None,
    "use_npy": False,
    "data_split_seed": None,
    "valid_exp": None,
    "norm_method":"layer",
    "slurm_config": None,
}
_param_defaults_dannce = {
    "metric": ["euclidean_distance_3D"],
    "sigma": 10,
    "lr": 1e-3,
    "n_layers_locked": 2,
    "interp": "nearest",
    "depth": False,
    "rotate": True,
    "comthresh": 0,
    "weighted": False,
    "com_method": "median",
    "channel_combo": None,
    "new_last_kernel_size": [3, 3, 3],
    "n_channels_out": 20,
    "cthresh": None,
    "medfilt_window": None,
    "com_fromlabels": False,
    "augment_continuous_rotation": False,
    "dannce_train_dir": None,
    "dannce_predict_dir": None,
    "dannce_predict_model": None,
    "dannce_finetune_weights": None,
    "com_file": None,
    "vmin": None,
    "vmax": None,
    "nvox": None,
    "expval": None,
    "com_thresh": None,
    "start_sample": None,
    "max_num_samples": None,
    "new_n_channels_out": None,
    "cam3_train": None,
    "debug_volume_tifdir": None,
    "vol_size": None,
    "train_mode": None,
    "downfac": None,
    "net_type": None,
    "net": None,
    "lr_scheduler": None,
    "from_weights": None,
    "dannce_predict_vol_tifdir": None,
    "n_rand_views": 0,
    "rand_view_replace": True,
    "multi_gpu_train": False,
    "heatmap_reg": False,
    "heatmap_reg_coeff": 0.01,
    "save_pred_targets": False,
    "huber-delta": 1.35,            #Change Adapted from implementation by Rob
    "avg+max": None,
    ## changes made to temporal
    "temporal_chunk_size": None,
    "temporal_loss_weight": None,
    "silhouette_loss_weight": None,
    "separation_loss_weight": None
}
_param_defaults_com = {
    "dsmode": "nn",
    "sigma": 30,
    "debug": False,
    "lr": 5e-5,
    "net": "unet2d_fullbn",
    "n_channels_out": 1,
    "com_train_dir": None,
    "com_predict_dir": None,
    "com_finetune_weights": None,
    "com_predict_weights": None,
    "com_debug": None,
    "com_exp": None,
    "n_channels_out": 1,
    "augment_rotation": False,
    "augment_shear": False,
    "augment_zoom": False,
    "augment_shift": False,
    "augment_shear_val": 5,
    "augment_zoom_val": 0.05,
    "augment_shift_val": 0.05,
}
