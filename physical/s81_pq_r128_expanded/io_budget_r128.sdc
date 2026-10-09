# DS-ROM field spine v13b (margin-first) ROUTING boundary (--sdc-append of phys13.sh; units ps), the PLAIN form.
# Die-integration IO budget (owner rule 2026-10-06 + clarification): the neighbour (die station, another clock region)
# launches / captures on a clock arriving at the block's own boundary-register clock arrival +/- 150 ps, with 100 ps
# wire + station clk-q on the late side (max 250), and a 50 ps hold IO uncertainty (min -50).
# This file is the form every stage LOADS (ideal clock, no network latency: pre-CTS both ends sit at 0).  From CTS on
# the hooks io_ref_pre.tcl / io_ref_post.tcl (PRE_/POST_CTS, PRE_/POST_GLOBAL_ROUTE) re-reference the same delays to
# the boundary registers' clock pins (-reference_pin q_go / o_ready), so each corner (WC and BC in the repair) times
# the boundary at its own propagated arrival; they apply it only after the timing graph exists (OpenSTA segfaults in
# Sim::findDisabledEdges when a graph is BUILT with -reference_pin delays present: v13b try1 3_3_place_gp) and put
# the plain form back before the stage writes its SDC.  Sign-off: signoff_r<R>.sdc (same budget, virtual clocks at
# each corner's measured arrival).
# v13 used a fixed measured insertion (650 / 850 ps) as a neighbour clock's source latency: post-CTS that asked the
# BC hold repair for ~420 ps on every R = 128 output and ~320 ps on every R = 16 input (WC insertion grew to ~820).
set fs_in [get_ports {go i_ph* i_np* i_xbase* i_xps* i_obase* i_ops* i_fmt* x_q* r_v* r_row* r_pos* r_fp32* r_bf16* r_e* f_fault}]
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
set_input_delay  250 -max -clock core_clk $fs_in
set_input_delay  0 -min -clock core_clk $fs_in
set_output_delay 250 -max -clock core_clk [all_outputs]
set_output_delay -50 -min -clock core_clk [all_outputs]
# screen-fixture ROM write ports (the die's ROMs are macros, not written) and the reset (the die's synchronised tree)
set_false_path -from [get_ports {rw_ph rw_st rw_a* rw_d* rst_n}]
