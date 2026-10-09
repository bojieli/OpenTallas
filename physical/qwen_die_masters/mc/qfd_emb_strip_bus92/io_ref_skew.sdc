# die-context boundary per domain, referenced to the propagated arrival L at a register of that domain's tree:
# 0.2 T outside + 150 ps (die wire to another region; 90 ps for the --intra domains), hold allowance 50 ps
set ot_hk [expr {[info exists ::env(OT_IO_HOLD_SKEW)] ? $::env(OT_IO_HOLD_SKEW) : 50}]
sta::worst_slack_cmd max
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
foreach {clk sk ins outs} {
  clk 150 {link_i[*] ret0[*] ret1[*] ret2[*] ret3[*] ret4[*] ret5[*] ret6[*] ret7[*] ret8[*] ret9[*] ret10[*] ret11[*] ret12[*] ret13[*] ret14[*] ret15[*] ret16[*] ret17[*] ret18[*] ret19[*] ret20[*] ret21[*] ret22[*] ret23[*] ret24[*] ret25[*] ret26[*] ret27[*] ret28[*] ret29[*] ret30[*] ret31[*]} {link_o[*] cmd0[*] cmd1[*] cmd2[*] cmd3[*] cmd4[*] cmd5[*] cmd6[*] cmd7[*] cmd8[*] cmd9[*] cmd10[*] cmd11[*] cmd12[*] cmd13[*] cmd14[*] cmd15[*] cmd16[*] cmd17[*] cmd18[*] cmd19[*] cmd20[*] cmd21[*] cmd22[*] cmd23[*] cmd24[*] cmd25[*] cmd26[*] cmd27[*] cmd28[*] cmd29[*] cmd30[*] cmd31[*] fault fault_code[*] ce_cnt[*] ue_info[*]}
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
set_false_path -from [get_ports {rst_n}]
