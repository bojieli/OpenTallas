# ot_fwd_link_hop2 fixture (physical/rom_clock/ot_fwd_link_hop2.sv): one clock at the west port; stage B is clocked
# by stage A's forwarded (inverted) clock, propagated through A's inverter and its own CTS subtree, so the A -> B
# hop is checked with the real forwarded-clock insertion.  B forwards fclk_o = ~~fclk_i (same polarity as fclk_i).
create_clock -name incoming -period 833.333 [get_ports fclk_i]
create_generated_clock -name forwarded -source [get_ports fclk_i] -edges {1 2 3} [get_ports fclk_o]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_input_delay 166.666 -clock incoming [get_ports {rst_n i_v i_d*}]
# B's outputs feed the next stage, which captures on the falling edge of B's forwarded clock (fwd_w512.sdc rule).
set_output_delay 166.666 -clock forwarded -clock_fall [get_ports {o_v o_d*}]
set_max_fanout 32 [current_design]
