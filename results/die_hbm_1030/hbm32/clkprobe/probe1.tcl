# DIE-HBM-32 diagnostic: stage composition of the core clock tree (TT, placement RC) on 4_cts.odb
set P /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f [glob $P/*RVT_TT*.lib* $P/*LVT_TT*.lib* $P/*SLVT_TT*.lib*] { read_liberty $f }
read_db $::env(RES)/4_1_cts.odb
read_sdc $::env(RES)/4_cts.sdc
source /work/setRC_rcx.tcl
set_propagated_clock [all_clocks]
estimate_parasitics -placement
source /work/pinreg_measure.tcl
source /work/clock_family.tcl
set clk [lindex [all_clocks] 0]
set prs [ot_pinreg_set]
set vals {}
dict for {i p} $prs { set a [ot_pinreg_arr $p $clk]; if {$a ne ""} { lappend vals [list $a $p] } }
set vals [lsort -real -index 0 $vals]
set n [llength $vals]
set s 0; foreach v $vals { set s [expr {$s + [lindex $v 0]}] }
puts "PROBE pinregs $n mean [format %.1f [expr {$s/$n}]] min [lindex $vals 0 0] max [lindex $vals end 0]"
# walk the clock net from the CK pin of the median register back to the port
set med [lindex $vals [expr {$n/2}] 1]
puts "PROBE median pin [get_full_name $med] arr [lindex $vals [expr {$n/2}] 0]"
set pin $med
set k 0
while {$k < 40} {
  set net [get_nets -of_objects $pin]
  set drv [get_pins -quiet -of_objects $net -filter "direction==output"]
  if {![llength $drv]} { puts "PROBE stage port [get_full_name $net]"; break }
  set inst [get_cells -of_objects $drv]
  set m [get_property $inst ref_name]
  set ai [get_property $drv arrival_max_rise]
  set fo [llength [get_pins -of_objects $net -filter "direction==input"]]
  puts "PROBE stage $k [get_full_name $inst] $m out_arr $ai fanout $fo"
  set ip [get_pins -of_objects $inst -filter "direction==input"]
  set pin [lindex $ip 0]
  incr k
}
