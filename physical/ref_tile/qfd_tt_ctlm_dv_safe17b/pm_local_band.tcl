# CODEX-QELEMENTS safe17: preserve the complete PM interface cones beside
# the two SRAM east faces. No cell/net/clock/RTL insertion and no latency change.
# Run after lp_cone_regions has assigned root ownership, before global placement.
namespace eval ot_pmb {
 variable block [ord::get_db_block]
 variable members [dict create]
 variable seen [dict create]
}
proc ot_pmb::walk {seeds direction} {
 variable seen; variable members
 set seen [dict create]; set queue $seeds
 for {set q 0} {$q < [llength $queue]} {incr q} {
  set net [lindex $queue $q]
  if {$net eq "NULL" || $net eq ""} continue
  set nn [$net getName]
  if {[dict exists $seen $nn]} continue
  dict set seen $nn 1
  foreach it [$net getITerms] {
   if {$direction eq "back" && ![$it isOutputSignal]} continue
   if {$direction eq "forward" && ![$it isInputSignal]} continue
   set inst [$it getInst]; set master [$inst getMaster]
   if {[$master isBlock] || [$inst isFixed]} continue
   # Only the core region owns PM logic. Preserve foreign-root landings.
   set old [$inst getGroup]
   if {$old ne "NULL" && $old ne "" && [$old getName] ne "ot_lcr_core"} continue
   dict set members [$inst getName] $inst
   if {[$master isSequential]} continue
   foreach p [$inst getITerms] {
    if {[$p getSigType] in {POWER GROUND CLOCK}} continue
    if {$direction eq "back" && [$p isInputSignal]} {lappend queue [$p getNet]}
    if {$direction eq "forward" && [$p isOutputSignal]} {lappend queue [$p getNet]}
   }
  }
 }
}
set ot_pmb_in {}; set ot_pmb_out {}; set ot_pmb_macros 0
foreach inst [$ot_pmb::block getInsts] {
 if {![string match {u_gi.u_cal.g_m*.*u_p192} [$inst getName]]} continue
 if {![[$inst getMaster] isBlock]} continue
 incr ot_pmb_macros
 foreach it [$inst getITerms] {
  if {[$it getSigType] in {POWER GROUND CLOCK}} continue
  if {[$it isInputSignal]} {lappend ot_pmb_in [$it getNet]}
  if {[$it isOutputSignal]} {lappend ot_pmb_out [$it getNet]}
 }
}
if {$ot_pmb_macros != 2} {error "OT_PMB expected two PM SRAMs, found $ot_pmb_macros"}
ot_pmb::walk $ot_pmb_in back
ot_pmb::walk $ot_pmb_out forward
set ot_pmb_region [odb::dbRegion_create $ot_pmb::block ot_lcr_pm]
set ot_pmb_dbu [$ot_pmb::block getDbUnitsPerMicron]
lassign {226.8 129.6 453.6 604.8} ot_pmb_x0 ot_pmb_y0 ot_pmb_x1 ot_pmb_y1
odb::dbBox_create $ot_pmb_region [expr {int($ot_pmb_x0*$ot_pmb_dbu)}] [expr {int($ot_pmb_y0*$ot_pmb_dbu)}] [expr {int($ot_pmb_x1*$ot_pmb_dbu)}] [expr {int($ot_pmb_y1*$ot_pmb_dbu)}]
$ot_pmb_region setRegionType INCLUSIVE
set ot_pmb_group [odb::dbGroup_create $ot_pmb_region ot_lcr_pm]
# Carve the dedicated band out of the old core fence: no overlapping regions.
set ot_pmb_core [$ot_pmb::block findRegion ot_lcr_core]
if {$ot_pmb_core eq "NULL"} {error "OT_PMB missing core region"}
set ot_pmb_boxes {}
foreach b [$ot_pmb_core getBoundaries] {
 lassign [list [expr {[$b xMin]/double($ot_pmb_dbu)}] [expr {[$b yMin]/double($ot_pmb_dbu)}] [expr {[$b xMax]/double($ot_pmb_dbu)}] [expr {[$b yMax]/double($ot_pmb_dbu)}]] x0 y0 x1 y1
 set ix0 [expr {max($x0,$ot_pmb_x0)}]; set iy0 [expr {max($y0,$ot_pmb_y0)}]
 set ix1 [expr {min($x1,$ot_pmb_x1)}]; set iy1 [expr {min($y1,$ot_pmb_y1)}]
 if {$ix0 >= $ix1 || $iy0 >= $iy1} {lappend ot_pmb_boxes [list $x0 $y0 $x1 $y1]} else {
  foreach box [list [list $x0 $y0 $ix0 $y1] [list $ix1 $y0 $x1 $y1] [list $ix0 $y0 $ix1 $iy0] [list $ix0 $iy1 $ix1 $y1]] {
   lassign $box a b0 c d
   if {$c > $a && $d > $b0} {lappend ot_pmb_boxes $box}
  }
 }
 odb::dbBox_destroy $b
}
foreach box $ot_pmb_boxes {
 lassign $box a b c d
 odb::dbBox_create $ot_pmb_core [expr {round($a*$ot_pmb_dbu)}] [expr {round($b*$ot_pmb_dbu)}] [expr {round($c*$ot_pmb_dbu)}] [expr {round($d*$ot_pmb_dbu)}]
}
set ot_pmb_area 0.0; set ot_pmb_n 0
foreach inst [dict values $ot_pmb::members] {
 set old [$inst getGroup]
 if {$old ne "NULL" && $old ne ""} {$old removeInst $inst}
 $ot_pmb_group addInst $inst
 set m [$inst getMaster]
 set ot_pmb_area [expr {$ot_pmb_area + [$m getWidth]*double([$m getHeight])/($ot_pmb_dbu*double($ot_pmb_dbu))}]
 incr ot_pmb_n
}
set ot_pmb_capacity [expr {($ot_pmb_x1-$ot_pmb_x0)*($ot_pmb_y1-$ot_pmb_y0)}]
set ot_pmb_util [expr {$ot_pmb_area/$ot_pmb_capacity}]
if {$ot_pmb_n < 100} {error "OT_PMB incomplete cone ownership: $ot_pmb_n cells"}
if {$ot_pmb_util > 0.60} {error "OT_PMB band needs enlargement: util=$ot_pmb_util"}
puts "OT_PMB PASS macros=$ot_pmb_macros cells=$ot_pmb_n area_um2=$ot_pmb_area band={226.8 129.6 453.6 604.8} util=$ot_pmb_util; unchanged nets/clocks/latency"
