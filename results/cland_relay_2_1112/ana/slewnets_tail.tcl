# ---- CLAND-RELAY-2 analysis tail (appended to a copy of the kit's signoff TT session head) ----
set_propagated_clock [all_clocks]
report_check_types -max_slew -violators > /out/slew.rpt
set c [open /out/slew.rpt]; set rpt [read $c]; close $c
set nets {}
puts "CR2 SLEWCOUNT [sta::max_slew_violation_count] rptlen [string length $rpt]"
set dbg [open /out/rpt.txt w]; puts $dbg $rpt; close $dbg
foreach line [split $rpt "\n"] {
  if {[regexp {^(\S+)\s+[0-9.]+\s+([0-9.]+)\s+(-[0-9.]+)\s+\(VIOLATED\)} $line -> pin slew slk]} {
    set p [get_pins -quiet $pin]
    if {$p eq ""} continue
    set n [get_nets -quiet -of_objects $p]
    if {$n eq ""} continue
    set nn [get_full_name $n]
    if {![dict exists $nets $nn]} { dict set nets $nn [list 0 0] }
    lassign [dict get $nets $nn] c w
    dict set nets $nn [list [expr {$c+1}] [expr {max($w,$slew)}]]
  }
}
set fp [open /out/slewnets.tsv w]
puts $fp "net\tviol_pins\tworst_slew\tdriver\tdriver_cell\tfanout\tpin_cap\twire_cap\ttotal_cap"
dict for {nn v} $nets {
  set n [get_nets $nn]
  set drv ""; set dc ""; set fo 0
  foreach p [get_pins -quiet -of_objects $n] {
    if {[get_property $p direction] eq "output"} { set drv [get_full_name $p]; set dc [get_property [get_cells -of_objects $p] ref_name] } else { incr fo }
  }
  report_net -digits 4 $nn > /out/net.tmp
  set c [open /out/net.tmp]; set r [read $c]; close $c
  set pc nan; set wc nan; set tc nan
  regexp {Pin capacitance:\s+([0-9.]+)} $r -> pc
  regexp {Wire capacitance:\s+([0-9.]+)} $r -> wc
  regexp {Total capacitance:\s+([0-9.]+)} $r -> tc
  puts $fp "$nn\t[lindex $v 0]\t[lindex $v 1]\t$drv\t$dc\t$fo\t$pc\t$wc\t$tc"
}
close $fp
puts "CR2 slew nets [dict size $nets]"
