# Corner-true vclk sign-off of a spine die view (approved common recipe 2026-10-06, the stations stn_margin_sdc.py
# FF file adapted to the spine io_vclk_m SDC; read by corner_sta.py --post-sdc after set_propagated_clock, in each
# corner's own session):
#   SS session: unchanged (setup against vclk at the SS insertion the flow measured; the 150 ps die-arrival term
#               stays in the 0.2 T + 150 ps IO budget).
#   FF session: outputs timed against vclk at this block's FF MINIMUM insertion, inputs launched at its FF MAXIMUM
#               insertion (the neighbour's die-clock leaf is within this block's own leaf spread), 50 ps IO hold
#               uncertainty between vclk and core_clk.
#   both:       the die reset (rst / por) reaches only the wrapper's two-flop synchroniser rst_s: false path.
foreach ot_p {rst[0] por} { if {[llength [get_ports -quiet $ot_p]]} { set_false_path -from [get_ports $ot_p] } }
if {[llength [get_libs -quiet *_FF_*]] && [llength [get_clocks -quiet vclk]]} {
  sta::redirect_string_begin
  report_clock_latency -clocks core_clk
  set ot_s [sta::redirect_string_end]
  if {[regexp {rise -> rise.*?([0-9.]+)\s+([0-9.]+)\s+latency} $ot_s -> ot_lo ot_hi]} {
    set_clock_latency $ot_lo [get_clocks vclk]
    set_output_delay -min 0 -clock vclk [all_outputs]
    set_input_delay -min [expr {$ot_hi - $ot_lo}] -clock vclk [all_inputs -no_clocks]
    set_clock_uncertainty -hold 50 -from [get_clocks vclk] -to [get_clocks core_clk]
    set_clock_uncertainty -hold 50 -from [get_clocks core_clk] -to [get_clocks vclk]
    puts "OT_VCLK_CT: FF insertion $ot_lo .. $ot_hi ps: outputs vs vclk $ot_lo, inputs launched at $ot_hi, IO hold uncertainty 50"
  } else {
    puts "OT_VCLK_CT: no core_clk latency report at FF"
  }
}
