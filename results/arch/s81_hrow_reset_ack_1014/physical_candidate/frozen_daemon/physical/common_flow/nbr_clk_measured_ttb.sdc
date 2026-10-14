# TT-BATCH copy of setup-triage nbr_clk_measured.sdc (b22c44d3a), guarded for blocks without a nbr_clk virtual clock.
# SETUP corners only (sourced after set_propagated_clock in the job's w18_sta_ss.tcl, which the loop's tt_resta.sh re-times
# at TT); the FF hold model keeps the generator SDC (hbm-blocks 9e81f6c70 OT_SMH_POST_SDC semantics).
if {[llength [get_clocks -quiet nbr_clk]]} {
  sta::redirect_string_begin
  report_clock_latency -clock core_clk
  set ot_s [sta::redirect_string_end]
  if {[regexp {rise -> rise.*?([0-9.]+)\s+([0-9.]+)\s+latency} $ot_s -> ot_lo ot_hi]} {
    set ot_L [expr {round(($ot_lo + $ot_hi) / 2.0)}]
    set_clock_latency -source $ot_L [get_clocks nbr_clk]
    puts "OT_NBR_MEASURED core_clk insertion $ot_lo .. $ot_hi -> nbr_clk source latency $ot_L"
  } else { puts "OT_NBR_MEASURED no latency report" }
} else { puts "OT_NBR_MEASURED no nbr_clk (unchanged)" }
