set calls {}
proc source {path} {}
proc ot_ser_balance {} {}
proc detailed_placement {} {}
proc estimate_parasitics {args} {}
proc ot_vclk_from_insertion {args} {}
proc all_outputs {} {return {{t_vm[0]} {t_vm[1663]} {t_st[0]} {t_st[63]} {t_ho[0]}}}
proc get_full_name {p} {return $p}
proc ot_clk_ins {corner clk} {if {$corner eq "WC"} {return {330 390}};return {180 220}}
proc get_clocks {c} {return $c}
proc unset_output_delay {args} {global calls;lappend calls [linsert $args 0 unset]}
proc set_clock_latency {args} {global calls;lappend calls [linsert $args 0 latency]}
proc set_output_delay {args} {global calls;lappend calls [linsert $args 0 delay]}
set fd [open physical/s81_ph_views/capture/post_cts_capt_domains.tcl];set hook [read $fd];close $fd
eval $hook
if {[llength $ot_serial_outputs] != 4 || [lsearch -exact $ot_serial_outputs {t_ho[0]}] >= 0} {error "wrong output classification"}
if {$ot_serial_L != 360 || $ot_serial_min != 140} {error "wrong per-corner budget"}
if {[lindex [lindex $calls 0] 2] ne "vclk" || [lindex [lindex $calls 2] 4] ne "vclk_s"} {error "wrong clock assignment"}
puts "PASS serial classification and measured WC/BC formula"
rename ot_clk_ins original_ins
proc ot_clk_ins {corner clk} {return {}}
if {![catch {eval $hook} msg]} {error "missing insertion accepted"}
if {![string match {*WC and BC serial insertion required*} $msg]} {error $msg}
puts "PASS missing measurement fails closed"
