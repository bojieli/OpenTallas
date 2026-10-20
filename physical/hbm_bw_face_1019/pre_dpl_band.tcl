# HBM-MC3G 10-20: release the FIRM pin cells (L2H-BW pre_dpl.tcl), then pull the GPL/repair births into the band.
source /src/physical/hbm_bw_face_1019/pre_dpl.tcl
source /src/physical/common_flow/std_band_fence.tcl
ot_band_fence_adopt pre_dpl
