# su_softmax round 5 die-boundary IO, route form (m5c).  m5b's generated io_clk at an internal flop CLK pin stopped
# CTS (CTS-0114 "Clock io_clk overlaps a previous clock"), so the route uses the virtual-clock convention of the other
# margin-rule views (physical/hbm_cp_pin_margin_20261006/io_vclk_m.sdc): IO delays against vclk whose SOURCE latency
# is the block's planning SS insertion L_SS (x6u40 calibration SS 834 / FF 520 ps; core_clk gets the same ideal
# latency so pre-CTS placement sees the IO at its post-CTS weight, as in io_vclk_m.sdc).  STA applies min/max latency
# as early/late per CLOCK ROLE, not per corner, so the FF hold budget is folded into the min IO delays instead:
# -min = budget - (L_SS - L_FF) on inputs (vclk launches), + (L_SS - L_FF) on outputs (vclk captures).  Hold is
# repaired at the FF corner only (route --hold-corners BC), where those values are exact.
# Budgets unchanged from boundary_io.sdc (time unit ps):
#   setup: 150 ps die clock arrival (different clock region) + clk->q 50 / setup 30 + 100 ps wire allowance
#   hold : 50 ps hold IO uncertainty, clk->q 20 / hold 10, no wire
# Sign-off re-times the IO against the routed block's measured per-corner insertion (io_budget.sh).
create_clock -name vclk -period [get_property [get_clocks core_clk] period]
set_clock_uncertainty -setup 60 [get_clocks vclk]
set_clock_uncertainty -hold 25 [get_clocks vclk]
set ot_lss 834
set ot_lff 520
set_clock_latency $ot_lss [get_clocks {core_clk vclk}]
set ot_all_in [all_inputs -no_clocks]
unset_input_delay -clock core_clk $ot_all_in
unset_output_delay -clock core_clk [all_outputs]
set ins {}
foreach p $ot_all_in { if {[get_name $p] ne "rst_n"} { lappend ins $p } }
set_input_delay -max 300 -clock vclk $ins
set_input_delay -min [expr {-30 - ($ot_lss - $ot_lff)}] -clock vclk $ins
set_output_delay -max 280 -clock vclk [all_outputs]
set_output_delay -min [expr {-60 + ($ot_lss - $ot_lff)}] -clock vclk [all_outputs]
