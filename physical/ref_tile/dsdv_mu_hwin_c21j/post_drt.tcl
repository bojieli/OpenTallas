# ref_tile POST_DETAIL_ROUTE: remove the pin-access keepout, restore the plain boundary SDC
source /src/physical/hbm_accel_die_views/stations/bench/stn_pin_keepout.tcl
source /src/physical/qwen_die_masters/post_plain.tcl
source /src/physical/qwen_die_masters/sram_edge_guard.tcl

source /src/physical/ref_tile/dsdv_mu_hwin_c21j/hwin_native_fences.tcl
ot_hj_fences_install
ot_hj_assign_births 0
ot_hj_fences_check post_drt.tcl
