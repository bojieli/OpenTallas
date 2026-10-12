# fill-8 2026-10-10: hfd_sfu_tile sign-off re-time (tools/w18/corner_sta.py --post-sdc): 833 ps, SS setup 60 ps / FF hold
# 25 ps, propagated clock, the faced tile's real IO phases (faced_io.sdc: falling-edge peer launch into the pin flops).
create_clock -name core_clk -period 833 [get_ports {clk}]
set_clock_uncertainty -setup 60 [get_clocks core_clk]
set_clock_uncertainty -hold 25 [get_clocks core_clk]
set_propagated_clock [get_clocks core_clk]
set fi_in [delete_from_list [all_inputs] [get_ports clk]]
set_input_delay -max 166.6 -clock core_clk -clock_fall $fi_in
set_input_delay -min 25 -clock core_clk -clock_fall $fi_in
set_output_delay -max 166.6 -clock core_clk [all_outputs]
set_output_delay -min -25 -clock core_clk [all_outputs]
