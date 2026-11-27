# repair_macro_clear.tcl (KV-INT-R3/FIRM 11-27, class C-REPAIR-BUF-OVER-MACRO).  Placement only, 0 cycles, no new cells, no net edit.
# Why: repair_design (timing-driven GPL and 3_4 resize) puts long-wire repeaters at the midpoint of a net.  A net that crosses a hard macro
# (KV pc / pc-fast / SRAM, ~290 x 270 um) gets repeaters INSIDE the macro footprint; no site exists there, so the diamond legaliser moves
# each one to the nearest free site (kv3_pc / pc_v1 / pc_v3: 627-1988 repeaters moved 100-256 um, 87-99.8 % of them from inside a macro or a
# hard placement blockage, 0 FIRM seats).  Here, right before DPL, every repair cell (default masters ^(BUF|INV|HB), status PLACED) whose
# centre lies in a hard macro box or hard placement blockage is moved to the exit of that rectangle that costs least: its own move plus the
# distance to the centroid of the instances on its nets.  DPL then only has to settle it (displacement of a few sites).
# Env: OT_RMC_HALO_UM (default 0.5, margin outside the rectangle), OT_RMC_MASTERS (regexp), OT_RMC_CENTROID_W (default 1.0).
# Report: OT_REPAIR_MACRO_CLEAR rects=R cells=N moved=M unresolved=U max_move_um=D (cells = repair cells found inside a rectangle).
proc ot_repair_macro_clear {} {
 set blk [ord::get_db_block]
 set dbu [expr {double([[ord::get_db_tech] getDbUnitsPerMicron])}]
 set halo [expr {int(round((([info exists ::env(OT_RMC_HALO_UM)] && $::env(OT_RMC_HALO_UM) ne "") ? double($::env(OT_RMC_HALO_UM)) : 0.5) * $dbu))}]
 set pat [expr {[info exists ::env(OT_RMC_MASTERS)] && $::env(OT_RMC_MASTERS) ne "" ? $::env(OT_RMC_MASTERS) : {^(BUF|INV|HB)}}]
 set cw [expr {([info exists ::env(OT_RMC_CENTROID_W)] && $::env(OT_RMC_CENTROID_W) ne "") ? double($::env(OT_RMC_CENTROID_W)) : 1.0}]
 set core [$blk getCoreArea]
 set cx0 [$core xMin]; set cx1 [$core xMax]; set cy0 [$core yMin]; set cy1 [$core yMax]
 set rects {}
 foreach i [$blk getInsts] {
  if {![[$i getMaster] isBlock]} continue
  set b [$i getBBox]
  lappend rects [list [expr {[$b xMin]-$halo}] [expr {[$b yMin]-$halo}] [expr {[$b xMax]+$halo}] [expr {[$b yMax]+$halo}]]
 }
 foreach o [$blk getBlockages] {
  if {[$o isSoft]} continue
  set b [$o getBBox]
  lappend rects [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]]
 }
 set g [expr {int(50*$dbu)}]
 set grid [dict create]
 set k 0
 foreach r $rects {
  lassign $r x0 y0 x1 y1
  for {set gx [expr {$x0/$g}]} {$gx <= $x1/$g} {incr gx} {
   for {set gy [expr {$y0/$g}]} {$gy <= $y1/$g} {incr gy} { dict lappend grid "$gx,$gy" $k }
  }
  incr k
 }
 set hit {}
 proc ot_rmc_in {grid rects g x y} {
  foreach k [expr {[dict exists $grid "[expr {$x/$g}],[expr {$y/$g}]"] ? [dict get $grid "[expr {$x/$g}],[expr {$y/$g}]"] : {}}] {
   lassign [lindex $rects $k] x0 y0 x1 y1
   if {$x > $x0 && $x < $x1 && $y > $y0 && $y < $y1} { return $k }
  }
  return -1
 }
 set n 0; set moved 0; set unres 0; set far 0
 foreach i [$blk getInsts] {
  set m [$i getMaster]
  if {[$m isBlock]} continue
  if {[$i getPlacementStatus] ne "PLACED"} continue
  if {![regexp $pat [$m getName]]} continue
  set b [$i getBBox]
  set w [expr {[$b xMax]-[$b xMin]}]; set h [expr {[$b yMax]-[$b yMin]}]
  set ox [$b xMin]; set oy [$b yMin]
  set cx [expr {$ox+$w/2}]; set cy [expr {$oy+$h/2}]
  set kk [ot_rmc_in $grid $rects $g $cx $cy]
  if {$kk < 0} continue
  incr n
  # centroid of the other instances on this cell's signal nets (nets of > 40 pins ignored)
  set sx 0.0; set sy 0.0; set sn 0
  foreach it [$i getITerms] {
   set net [$it getNet]
   if {$net eq "NULL" || [$net getSigType] ne "SIGNAL"} continue
   set its [$net getITerms]
   if {[llength $its] > 40} continue
   foreach t2 $its {
    set j [$t2 getInst]
    if {$j eq $i} continue
    set bb [$j getBBox]
    set sx [expr {$sx+([$bb xMin]+[$bb xMax])/2.0}]; set sy [expr {$sy+([$bb yMin]+[$bb yMax])/2.0}]; incr sn
   }
  }
  if {$sn > 0} { set tx [expr {$sx/$sn}]; set ty [expr {$sy/$sn}] } else { set tx $cx; set ty $cy }
  lassign [lindex $rects $kk] x0 y0 x1 y1
  # candidates: exit left / right / below / above; the free coordinate follows the centroid clamped to the rectangle span
  set py [expr {max($y0, min($y1-$h, int($ty-$h/2)))}]
  set px [expr {max($x0, min($x1-$w, int($tx-$w/2)))}]
  set cand [list [list [expr {$x0-$w}] $py] [list $x1 $py] [list $px [expr {$y0-$h}]] [list $px $y1]]
  set best {}; set bc 1e30
  foreach c $cand {
   lassign $c nx ny
   if {$nx < $cx0 || $ny < $cy0 || $nx+$w > $cx1 || $ny+$h > $cy1} continue
   if {[ot_rmc_in $grid $rects $g [expr {$nx+$w/2}] [expr {$ny+$h/2}]] >= 0} continue
   set mv [expr {abs($nx-$ox)+abs($ny-$oy)}]
   set cost [expr {$mv + $cw*(abs($nx+$w/2-$tx)+abs($ny+$h/2-$ty))}]
   if {$cost < $bc} { set bc $cost; set best [list $nx $ny $mv] }
  }
  if {$best eq {}} { incr unres; continue }
  lassign $best nx ny mv
  $i setLocation $nx $ny
  incr moved
  if {$mv/$dbu > $far} { set far [expr {$mv/$dbu}] }
 }
 puts [format "OT_REPAIR_MACRO_CLEAR rects=%d cells=%d moved=%d unresolved=%d max_move_um=%.1f" [llength $rects] $n $moved $unres $far]
}
ot_repair_macro_clear
