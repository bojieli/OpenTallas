read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob $::env(G)/macros/*.lef] { read_lef $f }
read_db $::env(ODB)
set b [ord::get_db_block]; set u [$b getDbUnitsPerMicron]
set L {34.572 354.252 725.772 1045.452}
set keep 0; set drop 0
foreach n [$b getNets] {
  if {[$n getSigType] eq "POWER" || [$n getSigType] eq "GROUND"} continue
  set lo 0; set hi 0
  foreach it [$n getITerms] { set r [$it getAvgXY]; if {[lindex $r 0]} { set y [expr {[lindex $r 2]/double($u)}]; if {$y <= 726.3} {set lo 1}; if {$y >= 993.1} {set hi 1} } }
  foreach bt [$n getBTerms] { set bb [$bt getBBox]; set y [expr {([$bb yMin]+[$bb yMax])/2.0/$u}]; if {$y <= 726.3} {set lo 1}; if {$y >= 993.1} {set hi 1} }
  if {$lo && $hi} { incr keep } else { foreach it [$n getITerms] { $it disconnect }; foreach bt [$n getBTerms] { odb::dbBTerm_destroy $bt }; incr drop }
}
puts "PROBE kept $keep crossing nets, dropped $drop"
set_routing_layers -signal M2-M7 -clock M2-M7
global_route -allow_congestion -verbose -congestion_report_file /out/probe_cong.rpt
