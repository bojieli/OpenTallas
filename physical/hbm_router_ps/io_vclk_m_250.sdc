# CLAUDE hbm-router: standalone block IO budget, owner margin-first form (same convention as the spine die views'
# io_vclk_m_<L>.sdc, claude/hbm-abstracts-spine-20261006 physical/hbm_accel_die_views/common): routed over-constrained
# (setup uncertainty 123 ps on the 833 ps clock = 770 ps effective), signed off at 833/60 by signoff_unc60.sdc
# (corner_sta --post-sdc); IO budget 0.2 T + 150 ps die clock-arrival allowance against vclk at the block's clock
# insertion L = 250 ps (every port is flop-direct in ot_gpu_router_topk_ps_core: S0 pin capture, out_* flops).
create_clock -name vclk -period [get_property [get_clocks core_clk] period]
set_clock_uncertainty -setup 123 [get_clocks {core_clk vclk}]
set_clock_uncertainty -hold 25 [get_clocks {core_clk vclk}]
set_clock_latency 250 [get_clocks vclk]
set ot_in [all_inputs -no_clocks]
unset_input_delay -clock core_clk $ot_in
unset_output_delay -clock core_clk [all_outputs]
set_input_delay [expr {[get_property [get_clocks core_clk] period] * 0.2 + 150}] -clock vclk $ot_in
set_output_delay [expr {[get_property [get_clocks core_clk] period] * 0.2 + 150}] -clock vclk [all_outputs]
set_input_delay -min 0 -clock vclk $ot_in
set_output_delay -min 0 -clock vclk [all_outputs]
