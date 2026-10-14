# ref_tile POST_DETAIL_ROUTE: remove the pin-access keepout, restore the plain boundary SDC
source /src/physical/hbm_accel_die_views/stations/bench/stn_pin_keepout.tcl
source /src/physical/qwen_die_masters/post_plain.tcl

# Published structural macroedge routing guard; toggle adds beforeGRT/removes afterDRT.
source /src/physical/common_flow/macro_edge_via_guard.tcl
