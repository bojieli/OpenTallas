# ref_tile POST_DETAIL_ROUTE: remove the pin-access keepout, restore the plain boundary SDC
source /src/physical/hbm_accel_die_views/stations/bench/stn_pin_keepout.tcl
source /src/physical/qwen_die_masters/post_plain.tcl
source /src/physical/qwen_die_masters/sram_edge_guard.tcl

source /src/physical/ref_tile/s81sl_lepnhwd_r3/lep_band.tcl
ot_lep_adopt_after_birth post_drt
ot_lep_band_check post_drt
