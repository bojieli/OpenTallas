# ---- DIE-QC-36 KITS BTAB QC-014 (A) east pin-column re-place (12.17(3) pair with (B)); from V1c (kit copy cut back
# to 3_2_place_iop): GPL with a hard blockage band x 261.738-264.330 over the g_btb[1]/[3] y-spans (removed before
# DPL), then the unchanged V1c flow (resize + max_wire_repeat 150, DPL, plan CTS, two-mode GRT hold, DRT), + planned
# repeaters on the V1c/V1d long-net slew list in grt_pre_core.tcl.  No clock ECO / pads / trims / new check.
override export PRE_GLOBAL_PLACE_TCL = /work/pre_gpl_a.tcl
override export PRE_DETAIL_PLACE_TCL = /work/pre_dpl_a.tcl
