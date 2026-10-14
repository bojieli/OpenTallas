# ref_tile POST_DETAIL_ROUTE: remove the pin-access keepout, restore the plain boundary SDC
source /src/physical/hbm_accel_die_views/stations/bench/stn_pin_keepout.tcl
source /src/physical/qwen_die_masters/post_plain.tcl
source /src/results/arch/hbm_native_1013/sm/physical_specs/smn_be_keep_root_gate.tcl
source /src/results/arch/hbm_native_1013/sm/physical_specs/smn_be_resize_legal.tcl
