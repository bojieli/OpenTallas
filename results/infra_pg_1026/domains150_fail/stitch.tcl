set ot_pg_maxgap 5.76

set ot_mesh_block [ord::get_db_block]
set ot_mesh_count 0
foreach ot_mesh_name {VDD VSS} {
 set ot_mesh_net [$ot_mesh_block findNet $ot_mesh_name];set ot_mesh_groups {}
 foreach sw [$ot_mesh_net getSWires] {foreach s [$sw getWires] {
  if {[$s isVia]} continue
  set layer [[$s getTechLayer] getName]
  if {$layer eq "M9"} {set key [list $layer [expr {([$s xMin]+[$s xMax])/2.0}]];set range [list [$s yMin] [$s yMax] [expr {[$s xMax]-[$s xMin]}]]} elseif {$layer eq "M8"} {set key [list $layer [expr {([$s yMin]+[$s yMax])/2.0}]];set range [list [$s xMin] [$s xMax] [expr {[$s yMax]-[$s yMin]}]]} else {continue}
  dict lappend ot_mesh_groups $key $range
 }}
 set ot_mesh_sw [odb::dbSWire_create $ot_mesh_net ROUTED];set ot_net_stitches 0
 foreach key [dict keys $ot_mesh_groups] {
  lassign $key layer center;set end -1e30;set prev_width 0
  foreach r [lsort -real -index 0 [dict get $ot_mesh_groups $key]] {
   lassign $r lo hi width
   if {$lo>$end && $lo-$end <= $ot_pg_maxgap*$dbu} {
    set half [expr {min($width,$prev_width)/2.0}]
    set aa [expr {round($center-$half)}];set cc [expr {round($center+$half)}]
    if {$layer eq "M9"} {set rect [list $aa $end $cc $lo]} else {set rect [list $end $aa $lo $cc]}
    set blocked 0
    if {$ot_mesh_name eq "VDD"} {foreach q $outer {if {[llength [ot_intersect $rect $q]]} {set blocked 1;break}}}
    if {!$blocked} {odb::dbSBox_create $ot_mesh_sw [[ord::get_db_tech] findLayer $layer] {*}$rect STRIPE;incr ot_net_stitches}
   }
   if {$hi>$end} {set prev_width $width;set end $hi}
  }
 }
 puts "OT_PG_SEAM_STITCHES $ot_mesh_name $ot_net_stitches"
 incr ot_mesh_count $ot_net_stitches
}
puts "OT_PG_CORE_SEAM_STITCHES $ot_mesh_count"
