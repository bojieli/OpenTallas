# qfd_hub sign-off at 833.333 ps (jobs/mk_mc_kit.py)
create_clock -name ck -period 833.333 [get_ports {ck}]
create_clock -name fck0 -period 833.333 [get_ports {fck0}]
create_clock -name fck1 -period 833.333 [get_ports {fck1}]
create_clock -name fck2 -period 833.333 [get_ports {fck2}]
create_clock -name fck3 -period 833.333 [get_ports {fck3}]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_propagated_clock [all_clocks]
# unrelated-clock crossings: one period minus the setup uncertainty, both directions; hold: non-negative
set_max_delay -ignore_clock_latency 773.333 -from [get_clocks ck] -to [get_clocks fck0]
set_min_delay -ignore_clock_latency 0 -from [get_clocks ck] -to [get_clocks fck0]
set_max_delay -ignore_clock_latency 773.333 -from [get_clocks ck] -to [get_clocks fck1]
set_min_delay -ignore_clock_latency 0 -from [get_clocks ck] -to [get_clocks fck1]
set_max_delay -ignore_clock_latency 773.333 -from [get_clocks ck] -to [get_clocks fck2]
set_min_delay -ignore_clock_latency 0 -from [get_clocks ck] -to [get_clocks fck2]
set_max_delay -ignore_clock_latency 773.333 -from [get_clocks ck] -to [get_clocks fck3]
set_min_delay -ignore_clock_latency 0 -from [get_clocks ck] -to [get_clocks fck3]
set_max_delay -ignore_clock_latency 773.333 -from [get_clocks fck0] -to [get_clocks ck]
set_min_delay -ignore_clock_latency 0 -from [get_clocks fck0] -to [get_clocks ck]
set_max_delay -ignore_clock_latency 773.333 -from [get_clocks fck0] -to [get_clocks fck1]
set_min_delay -ignore_clock_latency 0 -from [get_clocks fck0] -to [get_clocks fck1]
set_max_delay -ignore_clock_latency 773.333 -from [get_clocks fck0] -to [get_clocks fck2]
set_min_delay -ignore_clock_latency 0 -from [get_clocks fck0] -to [get_clocks fck2]
set_max_delay -ignore_clock_latency 773.333 -from [get_clocks fck0] -to [get_clocks fck3]
set_min_delay -ignore_clock_latency 0 -from [get_clocks fck0] -to [get_clocks fck3]
set_max_delay -ignore_clock_latency 773.333 -from [get_clocks fck1] -to [get_clocks ck]
set_min_delay -ignore_clock_latency 0 -from [get_clocks fck1] -to [get_clocks ck]
set_max_delay -ignore_clock_latency 773.333 -from [get_clocks fck1] -to [get_clocks fck0]
set_min_delay -ignore_clock_latency 0 -from [get_clocks fck1] -to [get_clocks fck0]
set_max_delay -ignore_clock_latency 773.333 -from [get_clocks fck1] -to [get_clocks fck2]
set_min_delay -ignore_clock_latency 0 -from [get_clocks fck1] -to [get_clocks fck2]
set_max_delay -ignore_clock_latency 773.333 -from [get_clocks fck1] -to [get_clocks fck3]
set_min_delay -ignore_clock_latency 0 -from [get_clocks fck1] -to [get_clocks fck3]
set_max_delay -ignore_clock_latency 773.333 -from [get_clocks fck2] -to [get_clocks ck]
set_min_delay -ignore_clock_latency 0 -from [get_clocks fck2] -to [get_clocks ck]
set_max_delay -ignore_clock_latency 773.333 -from [get_clocks fck2] -to [get_clocks fck0]
set_min_delay -ignore_clock_latency 0 -from [get_clocks fck2] -to [get_clocks fck0]
set_max_delay -ignore_clock_latency 773.333 -from [get_clocks fck2] -to [get_clocks fck1]
set_min_delay -ignore_clock_latency 0 -from [get_clocks fck2] -to [get_clocks fck1]
set_max_delay -ignore_clock_latency 773.333 -from [get_clocks fck2] -to [get_clocks fck3]
set_min_delay -ignore_clock_latency 0 -from [get_clocks fck2] -to [get_clocks fck3]
set_max_delay -ignore_clock_latency 773.333 -from [get_clocks fck3] -to [get_clocks ck]
set_min_delay -ignore_clock_latency 0 -from [get_clocks fck3] -to [get_clocks ck]
set_max_delay -ignore_clock_latency 773.333 -from [get_clocks fck3] -to [get_clocks fck0]
set_min_delay -ignore_clock_latency 0 -from [get_clocks fck3] -to [get_clocks fck0]
set_max_delay -ignore_clock_latency 773.333 -from [get_clocks fck3] -to [get_clocks fck1]
set_min_delay -ignore_clock_latency 0 -from [get_clocks fck3] -to [get_clocks fck1]
set_max_delay -ignore_clock_latency 773.333 -from [get_clocks fck3] -to [get_clocks fck2]
set_min_delay -ignore_clock_latency 0 -from [get_clocks fck3] -to [get_clocks fck2]
set ::env(OT_IO_HOLD_SKEW) 50
# die-context boundary per domain, referenced to the propagated arrival L at a register of that domain's tree:
# 0.2 T outside + 150 ps (die wire to another region; 90 ps for the --intra domains), hold allowance 50 ps
set ot_hk [expr {[info exists ::env(OT_IO_HOLD_SKEW)] ? $::env(OT_IO_HOLD_SKEW) : 50}]
sta::worst_slack_cmd max
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
foreach {clk sk ins outs} {
  ck 150 {x3_v x3_d[*] x3_tag[*] ar_cr} {x3_cr ar_v ar_d[*] fault l0_o[*] l1_o[*] l2_o[*] l3_o[*]}
  fck0 150 {l0_i[*]} {}
  fck1 150 {l1_i[*]} {}
  fck2 150 {l2_i[*]} {}
  fck3 150 {l3_i[*]} {}
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
