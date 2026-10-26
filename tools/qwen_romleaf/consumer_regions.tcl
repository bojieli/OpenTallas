# Place only each final transmit rung beside its actual LSL consumer.
# All eight transmit groups retain ck. Clock-root identity does not determine placement ownership.
# The caller supplies qrl_boxes keyed tx_final_0 .. tx_final_7 from parent_plan.json.
if {![info exists qrl_boxes]} {error "ROMleaf consumer boxes absent"}
set qrl_block [ord::get_db_block]
set qrl_dbu [$qrl_block getDbUnitsPerMicron]
set qrl_members [dict create]
foreach inst [$qrl_block getInsts] {
 set master [$inst getMaster]
 if {[$master isBlock] || ![$master isSequential]} {continue}
 set name [string map [list "\\" ""] [$inst getName]]
 if {[regexp {g_sl\[([0-7])\]\.g_hd\.g_tx\.g_r\[1\]\.u_tx/} $name -> leaf]} {
  dict lappend qrl_members tx_final_$leaf $inst
 }
}
set report [open qrl_consumer_regions.tsv w]
puts $report "group\tff_sinks\tcell_area_um2\trow_capacity_um2\tfill"
for {set leaf 0} {$leaf<8} {incr leaf} {
 set group_name tx_final_$leaf
 if {![dict exists $qrl_members $group_name] || [llength [dict get $qrl_members $group_name]]!=390} {
  error "ROMleaf final TX rung $leaf must own exactly390 mapped flops"
 }
 lassign [dict get $qrl_boxes $group_name] x0 y0 x1 y1
 set region [odb::dbRegion_create $qrl_block qrl_$group_name]
 $region setRegionType EXCLUSIVE
 odb::dbBox_create $region [expr {round($x0*$qrl_dbu)}] [expr {round($y0*$qrl_dbu)}] [expr {round($x1*$qrl_dbu)}] [expr {round($y1*$qrl_dbu)}]
 set group [odb::dbGroup_create $region qrl_$group_name]
 set area 0.0
 foreach inst [dict get $qrl_members $group_name] {
  if {[$inst getGroup] ne "NULL" && [$inst getGroup] ne ""} {error "ROMleaf consumer already owned: [$inst getName]"}
  $group addInst $inst
  set m [$inst getMaster]
  set area [expr {$area+double([$m getWidth])*[$m getHeight]/($qrl_dbu*$qrl_dbu)}]
 }
 # Count actual row intersections; macro/halo obstacles remain the ordinary flow's hard blockages.
 set capacity 0.0
 foreach row [$qrl_block getRows] {
  set bb [$row getBBox]
  set rx0 [expr {[$bb xMin]/double($qrl_dbu)}];set ry0 [expr {[$bb yMin]/double($qrl_dbu)}]
  set rx1 [expr {[$bb xMax]/double($qrl_dbu)}];set ry1 [expr {[$bb yMax]/double($qrl_dbu)}]
  set capacity [expr {$capacity+max(0.0,min($x1,$rx1)-max($x0,$rx0))*max(0.0,min($y1,$ry1)-max($y0,$ry0))}]
 }
 if {$capacity<=0 || $area/$capacity>0.60} {error "ROMleaf consumer $group_name cannot fit actual rows: $area / $capacity"}
 puts $report "$group_name\t390\t$area\t$capacity\t[expr {$area/$capacity}]"
}
close $report
puts "ROMLEAF_CONSUMER_GROUP_PASS 8groups3120finalrungFF actual_row_capacity_checked"
