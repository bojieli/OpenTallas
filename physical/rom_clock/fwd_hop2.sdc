# ot_fwd_link_hop2 fixture (physical/rom_clock/ot_fwd_link_hop2.sv): one clock at the west port; stage B is clocked
# by stage A's forwarded (inverted) clock fwd_a with its own CTS subtree, so the A -> B hop is checked with the real
# forwarded-clock insertion.  B forwards fclk_o = ~fwd_a (same polarity as fclk_i).
create_clock -name incoming -period 833.333 [get_ports fclk_i]
# Stage A's forwarded clock: generated at the last span repeater (u_rep5, after A's forwarding inverter and six
# repeaters: five inversions), the root of stage B's own subtree.  Its latency is propagated from fclk_i through A's
# tree leaf, the forwarding inverter and the repeated span, then B's subtree.
create_generated_clock -name fwd_a -source [get_ports fclk_i] -divide_by 1 -invert [get_pins {u_rep5/*/Y}]
create_generated_clock -name forwarded -source [get_pins {u_rep5/*/Y}] -master_clock fwd_a -divide_by 1 -invert [get_ports fclk_o]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_input_delay 166.666 -clock incoming [get_ports {rst_n i_v i_d*}]
# B's outputs feed the next stage, which captures on the falling edge of B's forwarded clock (fwd_w512.sdc rule).
set_output_delay 166.666 -clock forwarded -clock_fall [get_ports {o_v o_d*}]
set_max_fanout 32 [current_design]
