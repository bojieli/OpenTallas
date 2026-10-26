# ref_tile POST_DETAIL_ROUTE: remove the pin-access keepout, restore the plain boundary SDC
source /src/physical/hbm_accel_die_views/stations/bench/stn_pin_keepout.tcl
source /src/physical/ref_tile/hbm_su_static_kind0_l4_leaf1_1015/clock_entry.sdc
source /src/tools/ref_tile/signal_layer_audit.tcl
ot_ref_audit_signal_layers M5 M5 [file join $::env(RESULTS_DIR) signal_layer_audit.json]
