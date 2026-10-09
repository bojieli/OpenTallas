# mtp-hbm 2026-10-08: re-STA IO model for the 10-05 SS-era w18 routes of the DSpark control blocks (hbm-fmax-ctl,
# 0.2 T IO against the IDEAL core_clk edge, i.e. insertion L charged to every output and credited to every input).
# Read AFTER set_propagated_clock (meas_resta.py --append), before signoff_unc60 / vclk_corner_true /
# link_budget_consistent / io_ref_routed: replaces the route's IO model with the current HBM die-view convention
# (make_io_vclk.sh: IO against vclk at the block's insertion; io_ref_routed.sdc then moves vclk to the ROUTED
# boundary mean in each corner's session).  Max delays: 0.2 T + 150 ps die arrival (io_vclk_m); the consistent die-link
# split (link_budget_consistent.sdc, -add_delay) tightens them to T-60-R / T-60-S.  Min delays 0 (rule H1 via
# vclk_corner_true.sdc in the FF session).  No routing touched.
create_clock -name vclk -period [get_property [get_clocks core_clk] period]
set_clock_uncertainty -setup 60 [get_clocks vclk]
set_clock_uncertainty -hold 25 [get_clocks vclk]
set ot_in [all_inputs -no_clocks]
unset_input_delay -clock core_clk $ot_in
unset_output_delay -clock core_clk [all_outputs]
set_input_delay [expr {[get_property [get_clocks core_clk] period] * 0.2 + 150}] -clock vclk $ot_in
set_output_delay [expr {[get_property [get_clocks core_clk] period] * 0.2 + 150}] -clock vclk [all_outputs]
set_input_delay -min 0 -clock vclk $ot_in
set_output_delay -min 0 -clock vclk [all_outputs]
foreach ot_p {rst rst_n rst[0] por} { if {[llength [get_ports -quiet $ot_p]]} { set_false_path -from [get_ports $ot_p] } }
