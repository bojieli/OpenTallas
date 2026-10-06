# Actual existing service subregions. Retain original CP and cmdproc claims as obstructions.
set b [ord::get_db_block];set dbu [$b getDbUnitsPerMicron]
foreach {name bounds} {w2_child {250.56 43.2 509.76 302.4} w2_gateway {17.28 345.6 527.04 518.4} w2_inherited {17.28 600.48 527.04 1270.08}} {
 set r [odb::dbRegion_create $b $name];$r setRegionType EXCLUSIVE
 lassign $bounds x0 y0 x1 y1
 odb::dbBox_create $r [expr {round($x0*$dbu)}] [expr {round($y0*$dbu)}] [expr {round($x1*$dbu)}] [expr {round($y1*$dbu)}]
 set groups($name) [odb::dbGroup_create $r $name]
}
foreach bounds {{583.2 25.92 660.96 103.68} {700.272 600.48 1600.128 1270.08}} {
 lassign $bounds x0 y0 x1 y1
 odb::dbBlockage_create $b [expr {round($x0*$dbu)}] [expr {round($y0*$dbu)}] [expr {round($x1*$dbu)}] [expr {round($y1*$dbu)}]
}
set counts [dict create w2_child 0 w2_gateway 0 w2_inherited 0]
foreach i [$b getInsts] {
 if {[$i isFixed]} {continue}
 set outputs 0;set owner w2_inherited
 foreach t [$i getITerms] {
  if {[[$t getMTerm] getIoType] ne "OUTPUT"} {continue}
  incr outputs;set n [$t getNet];if {$n eq "NULL"} {continue};set nn [$n getName]
  if {[string match {*u_w2_sink.*} $nn] || $nn in {reserve_r source_permit retained done sink_req sink_req_v sink_rsp_r sink_retire_r sink_fault}} {set owner w2_child}
  if {[regexp {protected_transport.*u_(request|response)_cut[01]\.} $nn]} {set owner w2_gateway}
 }
 if {!$outputs} {continue}
 $groups($owner) addInst $i;dict incr counts $owner
}
foreach name [dict keys $counts] {if {![dict get $counts $name]} {error "Missing actual source cone $name"}}
puts "OT_W2_SOURCE_REGIONS $counts"
