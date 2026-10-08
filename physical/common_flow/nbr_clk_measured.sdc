# setup-triage IO fix (post-SDC, after set_propagated_clock): the virtual neighbour clock nbr_clk (the neighbour's clock) at THIS route's measured core_clk insertion (midpoint of
# the propagated latency), instead of the planning latency passed to tools/hbm_accel_smh_physical.py.
sta::redirect_string_begin
report_clock_latency -clock core_clk
set ot_s [sta::redirect_string_end]
if {[regexp {rise -> rise.*?([0-9.]+)\s+([0-9.]+)\s+latency} $ot_s -> ot_lo ot_hi]} {
  set ot_L [expr {round(($ot_lo + $ot_hi) / 2.0)}]
  set_clock_latency -source $ot_L [get_clocks nbr_clk]
  puts "OT_NBR_MEASURED core_clk insertion $ot_lo .. $ot_hi -> nbr_clk source latency $ot_L"
} else { puts "OT_NBR_MEASURED no latency report" }
# Proof (re-STA, no re-route) hbm_smh_front_n_m3f_f7f1a0ee4_t8: planning latency 688 vs measured 506..600 (mid 553):
# SS input->reg -53.6 -> +81.4, reg->output +64.8; the block's remaining SS limiter is reg2reg u_rl.u_d -> u_ol.u_d
# -108.6 (416 um, class F).  Use as a verdict post_sdc (SS); the FF hold model stays flow-hold's.
