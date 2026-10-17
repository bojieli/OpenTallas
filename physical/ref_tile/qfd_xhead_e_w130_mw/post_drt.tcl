# ref_tile POST_DETAIL_ROUTE: remove the pin-access keepout, restore the plain boundary SDC
source /src/physical/hbm_accel_die_views/stations/bench/stn_pin_keepout.tcl
source /src/physical/qwen_die_masters/post_plain.tcl
set ::ot_m6_pin_access_mode remove
set ::ot_m6_stub_um 0.384
source /src/physical/common_flow/m6_pin_access.tcl
