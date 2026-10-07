# Stateful SDC API stub: verify effective bounds, not just command presence.
set outputs {{t_vm[0]} {t_vm[1663]} {t_st[0]} {t_st[63]} {t_ho[0]}}
array set delay {}
foreach p $outputs {set delay(vclk,max,$p) 316.6666;set delay(vclk,min,$p) 107}
# Model the legacy serial setup constraint and the incorrectly reintroduced
# core min-delay. Also exercise recovery when a serial setup bound is missing.
foreach p [lrange $outputs 0 2] {set delay(vclk_s,max,$p) 372.2222}
proc source {path} {}
proc ot_ser_balance {} {}
proc detailed_placement {} {}
proc estimate_parasitics {args} {}
proc ot_vclk_from_insertion {args} {}
proc all_outputs {} {return $::outputs}
proc get_full_name {p} {return $p}
proc ot_clk_ins {corner clk} {if {$corner eq "WC"} {return {330 390}};return {180 220}}
proc get_clocks {c} {return $c}
proc get_property {obj prop} {if {$obj ne "ser_clk" || $prop ne "period"} {error "unexpected property"};return 1111.111}
proc unset_output_delay {args} {
 set clock [lindex $args [expr {[lsearch -exact $args -clock]+1}]]
 foreach p [lindex $args end] {foreach bound {min max} {unset -nocomplain ::delay($clock,$bound,$p)}}
}
proc set_clock_latency {args} {}
proc set_output_delay {args} {
 set clock [lindex $args [expr {[lsearch -exact $args -clock]+1}]]
 foreach bound {min max} {
  set ix [lsearch -exact $args -$bound]
  if {$ix>=0} {foreach p [lindex $args end] {set ::delay($clock,$bound,$p) [lindex $args [expr {$ix+1}]]}}
 }
}
set fd [open physical/s81_ph_views/capture/post_cts_capt_domains.tcl];set hook [read $fd];close $fd
eval $hook
foreach p [lrange $outputs 0 3] {
 foreach bound {min max} {
  if {[info exists delay(vclk,$bound,$p)]} {error "serial port retains core $bound: $p"}
  if {![info exists delay(vclk_s,$bound,$p)]} {error "serial port unconstrained $bound: $p"}
 }
 if {abs($delay(vclk_s,max,$p)-372.2222)>0.00001 || $delay(vclk_s,min,$p)!=140} {error "wrong effective serial bounds: $p"}
}
set p {t_ho[0]}
if {$delay(vclk,max,$p)!=316.6666 || $delay(vclk,min,$p)!=107 || [info exists delay(vclk_s,min,$p)]} {error "core output changed"}
puts "PASS all serial outputs have effective max372.2222/min140 on vclk_s only; core bounds preserved"
rename ot_clk_ins original_ins
proc ot_clk_ins {corner clk} {return {}}
if {![catch {eval $hook} msg] || ![string match {*WC and BC serial insertion required*} $msg]} {error "missing insertion did not fail closed"}
puts "PASS missing corner insertion fails closed"
