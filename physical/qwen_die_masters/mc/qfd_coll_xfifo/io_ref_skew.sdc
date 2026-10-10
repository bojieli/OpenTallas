# sys-takeover 2026-10-09: qfd_coll_xfifo (ot_qwen_die_coll_xfifo, the native collective local port): two
# unrelated clocks ck (collective) / ckd (sequencer), written from the qfd_io_xfifo kit pattern.
# die-context boundary per clock domain (post-CTS): referenced to the propagated arrival L at a register of the
# block's tree in that domain; 0.2 T outside + OT_IO_SKEW_INTER (every xfifo port crosses a die wire to another clock
# region: 150 ps), hold allowance OT_IO_HOLD_SKEW (50).
set ot_sk [expr {[info exists ::env(OT_IO_SKEW_INTER)] ? $::env(OT_IO_SKEW_INTER) : 150}]
set ot_hk [expr {[info exists ::env(OT_IO_HOLD_SKEW)] ? $::env(OT_IO_HOLD_SKEW) : 50}]
sta::worst_slack_cmd max
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
foreach {clk ins outs} {
  ck {o_seq_coll_cr i_coll_seq_v i_coll_seq[*]} {o_seq_coll_v o_seq_coll[*] fault_ck}
  ckd {i_seq_coll_v i_seq_coll[*] o_coll_seq_cr} {i_seq_coll_cr o_coll_seq_v o_coll_seq[*] fault_ckd}
} {
  set ref [lindex [all_registers -clock $clk -clock_pins] 0]
  set lmax [get_property $ref arrival_max_rise]; set lmin [get_property $ref arrival_min_rise]
  set T [get_property [get_clocks $clk] period]
  puts "QDM $clk ref [get_full_name $ref] L max $lmax min $lmin skew $ot_sk"
  set_input_delay  [expr {0.2*$T + $lmax + $ot_sk}] -max -clock $clk [get_ports $ins]
  set_input_delay  [expr {$lmin - ([info exists ::env(OT_IO_IN_HOLD_SKEW)] ? $::env(OT_IO_IN_HOLD_SKEW) : 0)}]          -min -clock $clk [get_ports $ins]
  set_output_delay [expr {0.2*$T - $lmax + $ot_sk}] -max -clock $clk [get_ports $outs]
  set_output_delay [expr {-$lmin - $ot_hk}]         -min -clock $clk [get_ports $outs]
}
set_false_path -from [get_ports rst_n]
