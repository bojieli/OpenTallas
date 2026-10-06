set_units -time ps -capacitance fF
create_clock -name core_clk -period 833.333333333 [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks core_clk]
set_clock_uncertainty -hold 25 [get_clocks core_clk]
# Conditional same-v9 planning cut; external launch insertion remains unqualified.
set_input_delay -min 360 -clock core_clk [get_ports {rst_n cfg_go cfg_ph* cfg_np* go e_sh_free e_bank_free external_cfg_q*}]
set_input_delay -max 727 -clock core_clk [get_ports {rst_n cfg_go cfg_ph* cfg_np* go e_sh_free e_bank_free external_cfg_q*}]
set_output_delay -min 360 -clock core_clk [all_outputs]
set_output_delay -max 727 -clock core_clk [all_outputs]
