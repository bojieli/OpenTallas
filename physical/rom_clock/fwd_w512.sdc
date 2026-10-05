# Falling-edge register and real inverted forwarded output waveform.
create_clock -name incoming -period 833.333 [get_ports fclk_i]
create_generated_clock -name forwarded -source [get_ports fclk_i] -edges {2 3 4} [get_ports fclk_o]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_input_delay 166.666 -clock incoming [get_ports {rst_n i_v i_d*}]
# Output is consumed at the next falling edge of the inverted clock (source rising).
set_output_delay 166.666 -clock forwarded -clock_fall [get_ports {o_v o_d*}]
set_max_fanout 32 [current_design]
