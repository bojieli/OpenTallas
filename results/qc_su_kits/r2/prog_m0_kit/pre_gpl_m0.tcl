# QC-SU-KITS-2 MIF0 PRE_GLOBAL_PLACE: pushdown (ck pin, die ft cells, entry root) + face pin registers + generic macro-pin
# flops.  The MIF1-only hooks (half_stage_band, row_ctrl_band, twd_band: g_rdhalf / g_wrrelay / write-relay banding)
# have no MIF0 cells and are not sourced.
source /work/pushdown.tcl
source /work/face_flops.tcl
source /work/cf/macro_pin_flops.tcl
