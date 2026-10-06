# Run only after Zeno loads actual final BODY ODB/SDC and corner-specific SPEF.
# Margin after60/25 is an AVAILABLE budget, not qualified source jitter/skew.
if {![info exists ::env(REPORTS_DIR)]} {error "REPORTS_DIR not bound"}
set dir $::env(REPORTS_DIR)
puts "WFC_BUDGET_SCOPE CONDITIONAL_BODY NO_CLOCK_SOURCE_OR_EXTERNAL_IO_CREDIT"
check_setup -verbose > $dir/wfc_external_IO_and_unconstrained.rpt
report_clock_properties [get_clocks {clk_fast clk_serial}] > $dir/wfc_input_clock_assumptions.rpt
foreach corner {WC BC} {
 foreach from {clk_fast clk_serial} {
  foreach to {clk_fast clk_serial} {
   foreach sense {max min} {
    # Register-to-register pairs include actual within-body CTS/network paths.
    # Unbound externalIO has a separate report and cannot be credited by these.
    report_checks -corner $corner -from [all_registers -clock $from -clock_pins] \
     -to [all_registers -clock $to -data_pins] -path_delay $sense \
     -format full_clock_expanded -group_path_count 40 -digits 6 \
     > $dir/wfc_budget_${corner}_${from}_${to}_${sense}.rpt
   }
  }
 }
}
