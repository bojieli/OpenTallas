# DS-ROM field spine v13b (margin-first) ROUTING boundary for the R = 16 screen (--sdc-append of phys13.sh; units ps).
# Die-integration IO budget (owner rule 2026-10-06 + clarification): the neighbour (die station, another clock region)
# launches / captures on a clock arriving at the block's own boundary-register clock arrival +/- 150 ps, with 100 ps
# wire + station clk-q on the late side, and a 50 ps hold IO uncertainty.
# v13b: the port delays are referenced to the boundary registers' clock pins (-reference_pin: q_go on the input side,
# o_ready on the output side), so every corner times the boundary against ITS OWN propagated arrival (WC and BC in
# the flow's repair, SS / FF at sign-off), and pre-CTS (ideal clock, no network latency) both ends sit at 0.
# v13 used a fixed measured insertion (650 / 850 ps) as the neighbour clock's source latency: post-CTS that asked the
# BC hold repair for ~420 ps on every R = 128 output (BC insertion ~525) and ~320 ps on every R = 16 input (WC
# insertion grew to ~820): 72,521 / 139,514 hold endpoints, repair stalled.  Measured on the v13 4_cts.odb with this
# file: R = 16 WC input hold -138 / BC -122, output BC -21 ps (the real boundary skew + 50 + 25).
# Same budget as signoff_r16.sdc (which uses virtual clocks with that arrival as source latency).
set fs_ref_i [get_pins {q_go$_DFF_P_/CLK}]
set fs_ref_o [get_pins {o_ready$_DFF_P_/CLK}]
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
set fs_in [get_ports {go i_ph* i_np* i_xbase* i_xps* i_obase* i_ops* i_fmt* x_q* r_v* r_row* r_pos* r_fp32* r_bf16* r_e* f_fault}]
set_input_delay  250 -max -clock core_clk -reference_pin $fs_ref_i $fs_in
set_input_delay  -50 -min -clock core_clk -reference_pin $fs_ref_i $fs_in
set_output_delay 250 -max -clock core_clk -reference_pin $fs_ref_o [all_outputs]
set_output_delay -50 -min -clock core_clk -reference_pin $fs_ref_o [all_outputs]
# screen-fixture ROM write ports (the die's ROMs are macros, not written) and the reset (the die's synchronised tree)
set_false_path -from [get_ports {rw_ph rw_st rw_a* rw_d* rst_n}]
