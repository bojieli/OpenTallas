# IOHOLD what-if: FF hold vs input min-delay contract (diagnostic, read-only on the kit 4_cts.odb)
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_FF*.lib* /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*LVT_FF*.lib*] { read_liberty $l }
read_db $::env(ODB)
read_sdc $::env(SDC)
set_propagated_clock [all_clocks]
source /work/vclk_corner.tcl
ot_vclk_bind ff
source /work/setRC_rcx.tcl
estimate_parasitics -placement
set vclk {}; set cps {}
foreach c [all_clocks] { set s [get_property $c sources]; if {![llength $s]} {lappend vclk $c}; foreach x $s {lappend cps [get_full_name $x]} }
set vclk [lindex $vclk 0]
set din {}; foreach p [all_inputs] { if {[get_full_name $p] ni $cps} { lappend din $p } }
set_output_delay -min 0 -clock $vclk [all_outputs]
# sender credit: output hold slack before repair (arrival - (vclk + 12.5)); min over outputs
set_input_delay -min -40 -clock $vclk $din
set op [find_timing_paths -path_delay min -to [all_outputs] -group_path_count 100000 -endpoint_path_count 1]
set os {}; foreach p $op { lappend os [sta::time_sta_ui [get_property $p slack]] }
set os [lsort -real $os]; set n [llength $os]
puts [format "OUT n %d min %.2f p10 %.2f p50 %.2f max %.2f" $n [lindex $os 0] [lindex $os [expr {$n/10}]] [lindex $os [expr {$n/2}]] [lindex $os end]]
foreach im $::env(INMINS) {
  set_input_delay -min $im -clock $vclk $din
  set w [sta::time_sta_ui [sta::worst_slack_cmd min]]
  set ne [sta::endpoint_violation_count min]
  set ps [find_timing_paths -path_delay min -group_path_count 200000 -endpoint_path_count 1 -slack_max 0]
  set nin 0; set nreg 0; array unset pad; set rw 0
  foreach p $ps {
    set sp [get_property $p startpoint]; set sl [sta::time_sta_ui [get_property $p slack]]
    if {[get_property $sp is_port]} { incr nin; set k [get_full_name $sp]; if {![info exists pad($k)] || $pad($k) < -$sl} { set pad($k) [expr {-$sl}] } } else { incr nreg; if {$sl < $rw} {set rw $sl} }
  }
  set pl {}; foreach k [array names pad] { lappend pl $pad($k) }; set pl [lsort -real $pl]; set np [llength $pl]
  set sum 0; foreach v $pl { set sum [expr {$sum + $v}] }
  if {$np} { set s [format "pad_ports %d p50 %.2f p90 %.2f max %.2f sum_ps %.0f" $np [lindex $pl [expr {$np/2}]] [lindex $pl [expr {$np*9/10}]] [lindex $pl end] $sum] } else { set s "pad_ports 0" }
  puts [format "INMIN %s wns %.2f nviol %d in_ep %d reg_ep %d reg_wns %.2f %s" $im $w $ne $nin $nreg $rw $s]
}
set_input_delay -min -40 -clock $vclk $din
report_checks -path_delay min -from $din -format full_clock_expanded -digits 2 -group_path_count 3
