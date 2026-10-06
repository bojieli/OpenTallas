# MARGIN (owner rule 2026-10-06): a die clock-arrival difference of OT_IO_SKEW ps (default 150) against this block's
# measured insertion is budgeted on every boundary delay, adversely: input launch later (setup) / earlier (hold),
# output capture earlier (setup) / later (hold).  Otherwise identical to the file named in the next line.
set ot_sk [expr {[info exists ::env(OT_IO_SKEW)] ? $::env(OT_IO_SKEW) : 150}]
# hold side (coordinator decision 2026-10-06): a 50 ps die-clock IO hold allowance (OT_IO_HOLD_SKEW), not the setup skew
set ot_hk [expr {[info exists ::env(OT_IO_HOLD_SKEW)] ? $::env(OT_IO_HOLD_SKEW) : 50}]
# from io_lat.sdc
# S1 die context, crash-free form of io_ref.sdc (post-CTS only).  OpenROAD 26Q3 segfaults in sta::Sim::findDisabledEdges
# when global routing evaluates slack with a -reference_pin boundary (qssr_570_* 5_1_grt, signal 11), so the same
# constraint is written with the clock port as reference and the propagated arrival at the reference register's CLK
# pin added explicitly.  It is the -reference_pin constraint evaluated at the moment it is read:
#   input  setup: launch = arr_max(ref) + 166.667        input  hold: launch = arr_min(ref) + 0
#   output setup: capture = arr_min(ref) - 166.667       output hold: capture = arr_max(ref) - 0
# Nothing is relaxed: setup keeps the 0.2 T outside budget, hold credits nothing outside the block.
# Exact only in a single-corner STA (one scalar arrival): used for sign-off (tools/w18/corner_sta.py --post-sdc, one
# corner per run) and endpoint grouping.  The multi-corner ORFS stages keep io_ref.sdc and run GRT with
# -critical_nets_percentage 0, the slack callback that crashed.
sta::worst_slack_cmd max   ;# builds the timing graph first: get_property arrival on an unbuilt graph segfaults
set qss_ref [get_pins {res_q\[0\]$_DFF_P_/CLK}]
set qss_amax [get_property $qss_ref arrival_max_rise]
set qss_amin [get_property $qss_ref arrival_min_rise]
puts "QSS ref arrival max $qss_amax min $qss_amin"
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
set qss_in  [get_ports {rst_n p_* res_in*}]
set qss_out [get_ports {o_we o_addr* o_mask* o_data* ov am_tv am_top* am_rmax fault}]
set_input_delay  [expr {166.667 + $qss_amax + $ot_sk}] -max -clock clk $qss_in
set_input_delay  [expr {$qss_amin - $ot_hk}]         -min -clock clk $qss_in
set_output_delay [expr {166.667 - $qss_amin + $ot_sk}] -max -clock clk $qss_out
set_output_delay [expr {-$qss_amax - $ot_hk}]        -min -clock clk $qss_out
