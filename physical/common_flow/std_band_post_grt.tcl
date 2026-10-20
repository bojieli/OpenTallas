# HBM-MC3G 10-20 (spec post_grt_extra): refresh the band role list after GRT repair (no cell is moved here).
source /src/physical/common_flow/std_band_fence.tcl
ot_band_fence_check post_grt
ot_band_fence_roles post_grt
