# PATH-QC 2026-10-26: A0 raw leaf lsl_rawfault_m3 sign-off SDC (GEOM-REVIEW-10 00:48 PASS-COND option A; GR-10 23:48 (2):
# "if COORD extends IO-HOLD A to QC, regenerate the SDC only").  CTS/placement unchanged.
# Leaf IO reference = the leaf's own pin-register insertion (hard core inside A0; the A0 parent balances it with
# OT_CORE_LAT): vclk TT 177.5 here, FF 143.9 via vclk_corner.tcl (OT_VCLK_FF) in the FF-only steps.
create_clock -name core_clk -period 833 [get_ports clk]
create_clock -name vclk -period 833.0000
set_clock_latency -source 177.5000 [get_clocks vclk]
set_clock_uncertainty 60.0000 -setup [all_clocks]
set_clock_uncertainty 25.0000 -hold [all_clocks]
# seam paths: uncertainty counted once per seam (COORD 16:58): 0.5 on each side
set_clock_uncertainty -from [get_clocks vclk] -to [get_clocks core_clk] -setup 30.0000
set_clock_uncertainty -from [get_clocks core_clk] -to [get_clocks vclk] -setup 30.0000
set_clock_uncertainty -from [get_clocks vclk] -to [get_clocks core_clk] -hold 12.5000
set_clock_uncertainty -from [get_clocks core_clk] -to [get_clocks vclk] -hold 12.5000
set non_clk_in [all_inputs -no_clocks]
set_input_delay -max 166.6000 -clock vclk $non_clk_in
set_output_delay -max 166.6000 -clock vclk [all_outputs]
set_input_delay -min -40.0000 -clock vclk $non_clk_in
# IO-HOLD A (COORD 10-26 00:19, two-sided 40 ps): vector data inputs take the A0 parent sender's checked 40 ps output-min;
# 1-bit scalars (v_d, first_d) and rst_n keep the -40 fallback (COORD 15:23).
set_input_delay -min 40.0000 -clock vclk [get_ports {split_d[*] w_d[*] x_d[*]}]
set_output_delay -min 0.0000 -clock vclk [all_outputs]
set_load 2 [all_outputs]
set_driving_cell -lib_cell BUFx4_ASAP7_75t_R -pin Y $non_clk_in
