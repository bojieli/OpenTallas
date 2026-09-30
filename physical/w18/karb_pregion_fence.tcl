# W18b: fence each K-arb slice of ot_chip_v41x_karb_pregion into its own pseudo-channel window
# (4 x 265.584 um, the legal e8p5 PHY), so the flat region places each slice as the closed pslice did.
# Flattened synthesis keeps the slice prefix only on flops ("g_s\[p\]."), so every unnamed cell is given
# the slice of the fenced cells it connects to (majority, up to 8 passes over nets of < 64 pins);
# cells tied to no slice or to two stay free.  ORFS POST_PDN hook: the regions persist in the odb.
set ot_block [ord::get_db_block]
set ot_dbu [$ot_block getDbUnitsPerMicron]
set ot_core [$ot_block getCoreArea]
set ot_win 265.584
set ot_glue_um 12.96   ;# free strip along the top edge (K tap / send ports) for the region glue
array unset ot_of
foreach inst [$ot_block getInsts] {
  set nm [$inst getName]
  if {[regexp {^g_s\\\[(\d)\\\]\.} $nm -> p]} { set ot_of([$inst getId]) $p }
}
for {set pass 0} {$pass < 8} {incr pass} {
  set add {}
  foreach inst [$ot_block getInsts] {
    set id [$inst getId]
    if {[info exists ot_of($id)] || [[$inst getMaster] getType] ne "CORE"} continue
    array unset cnt
    foreach it [$inst getITerms] {
      set net [$it getNet]
      if {$net eq "NULL" || [$net getSigType] ne "SIGNAL"} continue
      set its [$net getITerms]
      if {[llength $its] > 64} continue
      foreach o $its { set oid [[$o getInst] getId]; if {[info exists ot_of($oid)]} { incr cnt($ot_of($oid)) } }
    }
    set ks [array names cnt]
    if {[llength $ks] == 1} { lappend add $id [lindex $ks 0] }
  }
  foreach {id p} $add { set ot_of($id) $p }
  puts "OT_FENCE pass $pass added [expr {[llength $add] / 2}]"
  if {![llength $add]} break
}
for {set p 0} {$p < 4} {incr p} {
  set r [odb::dbRegion_create $ot_block "ot_slice$p"]
  set x0 [expr {max([$ot_core xMin], int($p * $ot_win * $ot_dbu) + 540)}]
  set x1 [expr {min([$ot_core xMax], int(($p + 1) * $ot_win * $ot_dbu) - 540)}]
  odb::dbBox_create $r $x0 [$ot_core yMin] $x1 [expr {[$ot_core yMax] - int($ot_glue_um * $ot_dbu)}]
  set ot_r($p) [odb::dbGroup_create $r "ot_slice${p}_g"]
  puts "OT_FENCE slice $p x [expr {$x0 / double($ot_dbu)}]-[expr {$x1 / double($ot_dbu)}]"
}
set n 0
foreach inst [$ot_block getInsts] {
  set id [$inst getId]
  if {[info exists ot_of($id)]} { $ot_r($ot_of($id)) addInst $inst; incr n }
}
puts "OT_FENCE fenced $n of [llength [$ot_block getInsts]]"
