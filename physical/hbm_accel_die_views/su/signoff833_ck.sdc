# CLAUDE HBM-ABSTRACTS (hub) sign-off re-time (owner margin rule 2026-10-06): the block is routed over-constrained
# (route clock CP < 0.833 ns) and signed off here at 833 ps / 60 / 25 with IO delays 0.2 x 833 + 150 ps die clock-arrival budget (tools/w18/corner_sta.py
# --post-sdc, read after the routed SDC: re-creates the clock on the same port).  Target SS >= +60 ps, FF >= +15 ps.
create_clock -name core_clk -period 833 [get_ports {ck[0]}]
set_clock_uncertainty -setup 60 [get_clocks core_clk]
set_clock_uncertainty -hold 25 [get_clocks core_clk]
set_propagated_clock [get_clocks core_clk]
set_input_delay 316.6 -clock core_clk [delete_from_list [all_inputs] [get_ports {ck[0]}]]
set_output_delay 316.6 -clock core_clk [all_outputs]
