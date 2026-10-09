# die-context boundary per domain, referenced to the propagated arrival L at a register of that domain's tree:
# 0.2 T outside + 150 ps (die wire to another region; 90 ps for the --intra domains), hold allowance 50 ps
set ot_hk [expr {[info exists ::env(OT_IO_HOLD_SKEW)] ? $::env(OT_IO_HOLD_SKEW) : 50}]
sta::worst_slack_cmd max
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
foreach {clk sk ins outs} {
  clk 150 {s_v w_v s_we s_bank[*] s_col[*] s_row[*] w_d[*]} {s_credit e_v e_d[*] fault_core}
  hclk 150 {cmd_v cmd[*] read_credit[*] r_v r_d[*]} {cmd_credit row_v row_op[*] row_bank[*] row_row[*] col_v col_we col_sr col_bank[*] col_col[*] busy wd[*] kv_v kv_d[*] fault_hbm}
} {
  set ref [lindex [all_registers -clock $clk -clock_pins] 0]
  set lmax [get_property $ref arrival_max_rise]; set lmin [get_property $ref arrival_min_rise]
  set T [get_property [get_clocks $clk] period]
  puts "QDM $clk ref [get_full_name $ref] L max $lmax min $lmin skew $sk"
  if {[llength $ins]} {
    set_input_delay  [expr {0.2*$T + $lmax + $sk}] -max -clock $clk [get_ports $ins]
    set_input_delay  [expr {$lmin - ([info exists ::env(OT_IO_IN_HOLD_SKEW)] ? $::env(OT_IO_IN_HOLD_SKEW) : 0)}]       -min -clock $clk [get_ports $ins] }
  if {[llength $outs]} {
    set_output_delay [expr {0.2*$T - $lmax + $sk}] -max -clock $clk [get_ports $outs]
    set_output_delay [expr {-$lmin - $ot_hk}]      -min -clock $clk [get_ports $outs] }
}
set_false_path -from [get_ports {rst_n hrst_n}]
