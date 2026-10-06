# OWNER-AUTHORIZED CONDITIONAL BODY DEFECTHUNT ONLY.
# External clock source ASSUMED/UNQUALIFIED; failed76158 is not instantiated.
# Units ps. Existing exact body bench tb_wfc_protected_stage starts both clocks
# high at a common epoch and uses50pct duty, ratio3:4. Use owner's exact periods,
# preserving that relationship instead of rounded bench decimal periods.
foreach p {fast_clk slow_clk clock_source_fault cold_n fast_rst_n slow_rst_n} {
 if {[llength [get_ports -quiet $p]] != 1} {
  error "Missing literal inputclock-body port $p"
 }
}
set wfc_body_conditional 1
set wfc_clock_source_qualified 0
set wfc_other_engine_IO_bound 0
set wfc_headline_allowed 0
create_clock -name clk_fast -period 833.333333333333 -waveform {0 416.666666666667} [get_ports fast_clk]
create_clock -name clk_serial -period 1111.111111111111 -waveform {0 555.555555555556} [get_ports slow_clk]
set_clock_uncertainty -setup 60 [get_clocks {clk_fast clk_serial}]
set_clock_uncertainty -hold 25 [get_clocks {clk_fast clk_serial}]
# Do not install invented source latency, source transition, jitter, input delay,
# output load, ideal NETWORK clock, falsepaths or asynchronous clock groups.
# Tool ideal SOURCE at input is a diagnostic assumption, not a measurement of
# zero insertion/slew/jitter. Actual body CTS/network parasitics remain enabled.
# All external fault/reset/engine/link/XB/C8 IO stays unbound and must appear in
# check_setup/coverage reports. Clock_source_fault is a real untied input.
# Final STA must propagate the actual body CTS and read each corner's SPEF.
puts "WFC_SCOPE CONDITIONAL_BODY IDEAL_EXTERNAL_INPUT_CLOCKS UNQUALIFIED_SOURCE UNBOUND_EXTERNAL_IO NO_HEADLINE"
