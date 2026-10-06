# S1 die context, per-corner form without -reference_pin (OpenROAD 26Q3 crashes in sta::Sim::findDisabledEdges when
# GRT asks for slack under a -reference_pin boundary).  A divide-by-1 generated clock defined at the reference
# register's CLK pin carries the propagated insertion of this block's tree to that pin in every corner; boundary
# delays referenced to it are the -reference_pin constraint (setup max 0.2 T, hold min 0; nothing relaxed).
# Post-CTS only (needs the built tree).
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
create_generated_clock -name clk_io -source [get_ports clk] -divide_by 1 [get_pins {res_q\[0\]$_DFF_P_/CLK}]
set_propagated_clock [get_clocks clk_io]
set_clock_uncertainty -setup 60 [get_clocks clk_io]
set_clock_uncertainty -hold 25 [get_clocks clk_io]
foreach {kind pats} {input {rst_n p_* res_in*} output {o_we o_addr* o_mask* o_data* ov am_tv am_top* am_rmax fault}} {
  set_${kind}_delay 166.667 -max -clock clk_io [get_ports $pats]
  set_${kind}_delay 0 -min -clock clk_io [get_ports $pats]
}
