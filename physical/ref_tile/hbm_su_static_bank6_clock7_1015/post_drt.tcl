# ref_tile POST_DETAIL_ROUTE: remove the pin-access keepout, restore the plain boundary SDC
source /src/physical/hbm_accel_die_views/stations/bench/stn_pin_keepout.tcl
source /src/physical/ref_tile/hbm_su_static_bank6_clock7_1015/clock_entry.sdc
source /src/physical/qwen_die_masters/sram_edge_guard.tcl
source /src/tools/ref_tile/signal_layer_audit.tcl
ot_ref_audit_signal_layers M5 M5 [file join $::env(RESULTS_DIR) signal_layer_audit.json]
