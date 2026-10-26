# Diagnostic native boundary model from the preserved CTS database, never a routed view.
source /src/tools/ref_tile/path_classes.tcl
foreach c [all_clocks] {
 set_clock_latency -source -early 0 $c
 set_clock_latency -source -late 0 $c
}
write_timing_model -library_name upipe96_cts_tt /work/upipe96_cts_tt.lib
puts "UPIPE96_CTS_NATIVE_ETM_DONE"
