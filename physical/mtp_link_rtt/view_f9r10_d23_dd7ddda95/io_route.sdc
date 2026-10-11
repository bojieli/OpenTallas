# IO against vclk at the measured SS insertion 292 ps, 0.2 T + 150 ps, FF-true hold mins
create_clock -name vclk -period [get_property [get_clocks core_clk] period]
set_clock_uncertainty -setup 60 [get_clocks vclk]
set_clock_uncertainty -hold 25 [get_clocks vclk]
# BEFORE CTS the real clock is ideal: its nominal interior network delay must
# equal the virtual reference. AFTER CTS set_propagated_clock ignores this
# ideal network latency and checks the actual tree; source remains local zero.
set_clock_latency 292 [get_clocks {core_clk vclk}]
# LOCAL BLOCK CHARACTERIZATION ONLY: clock port is the local time origin.
# Source0 is provisional, not option-1 die clock qualification. Before native
# adoption attach the actual balanced die-tree tap source latency and recheck
# boundary timing/lockups against the parent clock plan and corner budgets.
set_clock_latency -source 0 [get_clocks core_clk]
set ot_in [all_inputs -no_clocks]
unset_input_delay -clock core_clk $ot_in
unset_output_delay -clock core_clk [all_outputs]
set_input_delay [expr {[get_property [get_clocks core_clk] period] * 0.2 + 150}] -clock vclk $ot_in
set_output_delay [expr {[get_property [get_clocks core_clk] period] * 0.2 + 150}] -clock vclk [all_outputs]
set_input_delay -min [expr {245 - 292 - 25}] -clock vclk $ot_in
# CLAUDE s81-blocks 2026-10-07: sign fixed (was FMIN - L + 25 = -371 at L 1068 / FMIN 672: required = L + 25 - min
# became L + FMIN-free 1464 ps, the -356 / -525 GRT hold-repair walls of wsrc-m2 / m2big); now required = FMIN + 50 as the
# guarded FF sign-off (vclk latency FMIN, hold uncertainty 50)
set_output_delay -min [expr {292 - 227 - 25}] -clock vclk [all_outputs]
