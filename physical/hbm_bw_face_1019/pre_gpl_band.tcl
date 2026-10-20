# HBM-MC3G 10-20: the L2H-BW SAFE-face PRE_GLOBAL_PLACE hook, then the literal-lattice std-cell band fence
# (physical/common_flow/std_band_fence.tcl; band from env OT_BAND_Y = spec fill_reason.lattice_channel_bound.std_band_y_um).
source /src/physical/hbm_bw_face_1019/pre_gpl.tcl
source /src/physical/common_flow/std_band_fence.tcl
ot_band_fence_create
