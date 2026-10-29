source /w/libs_ff.tcl
set mode $::env(OT_MODE)
if {$mode eq "est"} { read_db /base/5_1_grt.odb } else { read_db /base/6_final.odb }
read_sdc /sdc/golden.sdc
set_propagated_clock [all_clocks]
foreach c [all_clocks] { if {[llength [get_property $c sources]]} { set_clock_latency -source 0 $c } }
if {$mode eq "est"} {
  source /work/setRC_rcx.tcl
  if {[info exists ::env(OT_RC)] && $::env(OT_RC) ne ""} { source $::env(OT_RC) }
  estimate_parasitics -global_routing
} else { read_spef /base/6_final.spef }
report_worst_slack -min
set blk [ord::get_db_block]
set f [open /w/${mode}$::env(OT_TAG).tsv w]
puts $f "net\tdrv\tnsink\tdrv_in\tdrv_out\tstage\twire_max\twire_cap"
set n 0
foreach net [$blk getNets] {
  if {[$net getSigType] ne "CLOCK"} continue
  set nm [$net getName]
  set snet [get_nets -quiet $nm]; if {![llength $snet]} continue
  set drv [get_pins -quiet -of_objects $snet -filter "direction==output"]
  if {[llength $drv] != 1} continue
  set inst [get_cells -of_objects $drv]
  set ain [get_pins -quiet -of_objects $inst -filter "direction==input"]
  set da ""; catch {set da [get_property $drv arrival_max_rise]}
  if {$da eq ""} continue
  set ia ""; if {[llength $ain]==1} { catch {set ia [get_property $ain arrival_max_rise]} }
  set wm 0; set ns 0
  foreach s [get_pins -quiet -of_objects $snet -filter "direction==input"] {
    set sa ""; catch {set sa [get_property $s arrival_max_rise]}
    if {$sa ne ""} { incr ns; set d [expr {$sa-$da}]; if {$d > $wm} {set wm $d} }
  }
  set wc "" 
  set st [expr {$ia eq "" ? "" : [format %.3f [expr {$da-$ia}]]}]
  puts $f "$nm\t[get_full_name $drv]\t$ns\t$ia\t$da\t$st\t[format %.3f $wm]\t$wc"
  incr n
}
close $f
set f [open /w/${mode}$::env(OT_TAG)_ck.tsv w]
foreach p [all_registers -clock_pins] { set a ""; catch {set a [get_property $p arrival_max_rise]}; puts $f "[get_full_name $p]\t$a" }
puts $f "HOLD\t[sta::time_sta_ui [sta::worst_slack_cmd min]]\t[sta::endpoint_violation_count min]"
puts $f "SETUP\t[sta::time_sta_ui [sta::worst_slack_cmd max]]\t[sta::endpoint_violation_count max]"
close $f
puts "PROBE nets $n"
catch {report_wire_length -net [list mp_ck_Tpq_br mp_ck_Tpqs_br mp_ck_Tpqsw_br] -global_route -detailed_route -verbose} e
puts "WL $e"
