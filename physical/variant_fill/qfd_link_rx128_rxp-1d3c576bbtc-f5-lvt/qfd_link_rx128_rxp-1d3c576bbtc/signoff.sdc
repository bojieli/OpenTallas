# safe-qwen S-A4 (2026-10-08): the o302 kits had NO signoff/<cfg>.sdc, so route_master.sh generated the single-clock template
# (core_clk on a non-existent port clk, OT_REF_GLOB *od_q*): the IO numbers of every o302 route (TT -695.9) were timed
# against no real clock.  This is signoff/qfd_link_rx128.sdc (wclk / rclk bound, per-domain die-context boundary).
# qfd_link_rx128 sign-off at 833.333 ps (jobs/mk_mc_kit.py)
create_clock -name wclk -period 833.333 [get_ports {wclk}]
create_clock -name rclk -period 833.333 [get_ports {rclk}]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_propagated_clock [all_clocks]
# unrelated-clock crossings: one period minus the setup uncertainty, both directions; hold: non-negative
set_max_delay -ignore_clock_latency 773.333 -from [get_clocks wclk] -to [get_clocks rclk]
set_min_delay -ignore_clock_latency 0 -from [get_clocks wclk] -to [get_clocks rclk]
set_max_delay -ignore_clock_latency 773.333 -from [get_clocks rclk] -to [get_clocks wclk]
set_min_delay -ignore_clock_latency 0 -from [get_clocks rclk] -to [get_clocks wclk]
set ::env(OT_IO_HOLD_SKEW) 50
# die-context boundary per domain, referenced to the propagated arrival L at a register of that domain's tree:
# 0.2 T outside + 150 ps (die wire to another region; 90 ps for the --intra domains), hold allowance 50 ps
set ot_hk [expr {[info exists ::env(OT_IO_HOLD_SKEW)] ? $::env(OT_IO_HOLD_SKEW) : 50}]
sta::worst_slack_cmd max
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
foreach {clk sk ins outs} {
  wclk 150 {i_v i_d[*]} {i_cr w_fault}
  rclk 150 {o_cr} {o_v o_d[*] r_fault}
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
set_false_path -from [get_ports {wrst_n rrst_n}]
