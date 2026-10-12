# [sfu] hbm-phys-1010 (copy of su/signoff833_ck8.sdc): the folded R25GQ SFU quarter's 8 die clock pins ck0..ck7 (one sub-tree per segment,
# all the same die clock): 833 ps / 60 / 25, IO delays 0.2 x 833 + 150 ps die clock-arrival budget on every data pin
# (each lands on a face-chain flop at the pin).  Read by tools/w18/corner_sta.py --post-sdc after the routed SDC.
create_clock -name core_clk -period 833 [get_ports {ck0 ck1 ck2 ck3 ck4 ck5 ck6 ck7}]
set_clock_uncertainty -setup 60 [get_clocks core_clk]
set_clock_uncertainty -hold 25 [get_clocks core_clk]
set_propagated_clock [get_clocks core_clk]
set_input_delay 316.6 -clock core_clk [delete_from_list [all_inputs] [get_ports {ck0 ck1 ck2 ck3 ck4 ck5 ck6 ck7}]]
set_output_delay 316.6 -clock core_clk [all_outputs]
