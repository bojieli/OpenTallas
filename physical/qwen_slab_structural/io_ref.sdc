# S1 die context (post-CTS only): every boundary register on the other side of these ports sits in the same band
# clock region (clocking decision C) and is balanced to the same insertion delay, so the launch/capture edge of each
# boundary delay is the PROPAGATED clock at a register of this block's tree (-reference_pin), not the ideal port
# edge.  Setup keeps the 0.2 T outside budget; hold credits nothing outside (-min 0: no source clk->q, no wire).
# Must be read AFTER load_design (OpenROAD 2026-10 segfaults in sta::Sim when a -reference_pin SDC is read at load).
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
set qss_ref [get_pins {res_q\[0\]$_DFF_P_/CLK}]
foreach {kind pats} {input {rst_n p_* res_in*} output {o_we o_addr* o_mask* o_data* ov am_tv am_top* am_rmax fault}} {
  set_${kind}_delay 166.667 -max -clock clk -reference_pin $qss_ref [get_ports $pats]
  set_${kind}_delay 0 -min -clock clk -reference_pin $qss_ref [get_ports $pats]
}
