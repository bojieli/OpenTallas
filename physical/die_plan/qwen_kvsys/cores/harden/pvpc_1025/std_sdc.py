import sys
clk, rst, tap = sys.argv[1], sys.argv[2], float(sys.argv[3])
per, ins, tol, io = 833.0, 250.0, 40.0, 0.2*833.0
s = "# KV-CORES/PV-PC 10-25: standard core SDC (gen_core_kit_kv.sdc vocabulary) for re-sign-off of a reused closed view\n"
s += f"create_clock -name clk -period {per:.4f} [get_ports {{{clk}}}]\n"
if tap: s += f"# CP2 early core tap: measured TT pin-flop mean - plan insertion 250\nset_clock_latency -source {tap:.4f} [get_ports {{{clk}}}]\n"
s += f"""create_clock -name vclk -period {per:.4f}
set_clock_latency -source {ins:.4f} [get_clocks vclk]
set_clock_uncertainty 60.0000 -setup [all_clocks]
set_clock_uncertainty 25.0000 -hold [all_clocks]
set_clock_uncertainty -from [get_clocks vclk] -to [get_clocks clk] -setup 30.0000
set_clock_uncertainty -from [get_clocks clk] -to [get_clocks vclk] -setup 30.0000
set_clock_uncertainty -from [get_clocks vclk] -to [get_clocks clk] -hold 12.5000
set_clock_uncertainty -from [get_clocks clk] -to [get_clocks vclk] -hold 12.5000
set non_clk_in [all_inputs -no_clocks]
set_input_delay -max {io:.4f} -clock vclk $non_clk_in
set_input_delay -min {-tol:.4f} -clock vclk $non_clk_in
set_output_delay -max {io:.4f} -clock vclk [all_outputs]
set_output_delay -min 0.0000 -clock vclk [all_outputs]
set_input_delay -max {0.5*per:.4f} -clock vclk [get_ports {{{rst}}}]
set_load 2 [all_outputs]
set_driving_cell -lib_cell BUFx4_ASAP7_75t_R -pin Y $non_clk_in
"""
print(s, end="")
