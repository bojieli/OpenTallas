# PRE_GLOBAL_ROUTE hook (CLAUDE HBM-ABSTRACTS stations, 2026-10-06): keep other nets out of the pin column.
# Why: die pin access (r8, and the stn_pa_check of P1_hfd_stn_r19 a[1029], Q1_hfd_gath_r10 a2[588], Q1_hfd_mcast_r7)
# failed where the block router ran neighbouring nets' vertical wires on the layers adjacent to the pin layer straight
# through the face pin column (P1_hfd_stn_r19: a[1020] / a[998] on M3 at x 59.841 / 59.913 over the M4 pin run, x
# 59.832-60.024), so the die router finds no via or planar access point that clears them.  This hook puts a routing
# obstruction on the two layers adjacent to each face's pin layer over that face's pin column (pin depth + OT_PK_HALO,
# default 0.072 um, along the full extent of the face's pin run plus the halo), so pins are reached on their own
# layer from inside.  The SAME file is also the POST_DETAIL_ROUTE hook: when the obstructions it computes already
# exist it removes exactly those again, so the routed odb and the exported abstract carry only real metal.
global pk_rects
set pk_halo [expr {[info exists ::env(OT_PK_HALO)] ? $::env(OT_PK_HALO) : 0.072}]
set pk_blk [ord::get_db_block]
set pk_tech [[ord::get_db] getTech]
set pk_dbu [$pk_blk getDbUnitsPerMicron]
set pk_h [expr {round($pk_halo * $pk_dbu)}]
set die [$pk_blk getDieArea]
set dx0 [$die xMin]; set dy0 [$die yMin]; set dx1 [$die xMax]; set dy1 [$die yMax]
array set ext {}
foreach bt [$pk_blk getBTerms] {
  if {[$bt getSigType] in {POWER GROUND}} continue
  foreach bp [$bt getBPins] {
    foreach bx [$bp getBoxes] {
      set l [$bx getTechLayer]; set ln [$l getName]
      set x0 [$bx xMin]; set y0 [$bx yMin]; set x1 [$bx xMax]; set y1 [$bx yMax]
      if {$x1 >= $dx1} { set f E } elseif {$x0 <= $dx0} { set f W } elseif {$y1 >= $dy1} { set f N } elseif {$y0 <= $dy0} { set f S } else { continue }
      set k "$f,$ln"
      if {![info exists ext($k)]} { set ext($k) [list $x0 $y0 $x1 $y1] } else {
        lassign $ext($k) a b c d
        set ext($k) [list [expr {min($a,$x0)}] [expr {min($b,$y0)}] [expr {max($c,$x1)}] [expr {max($d,$y1)}]]
      }
    }
  }
}
set pk_rects {}
foreach k [array names ext] {
  lassign [split $k ,] f ln
  lassign $ext($k) x0 y0 x1 y1
  switch $f {
    E { set r [list [expr {$x0 - $pk_h}] [expr {$y0 - $pk_h}] $dx1 [expr {$y1 + $pk_h}]] }
    W { set r [list $dx0 [expr {$y0 - $pk_h}] [expr {$x1 + $pk_h}] [expr {$y1 + $pk_h}]] }
    N { set r [list [expr {$x0 - $pk_h}] [expr {$y0 - $pk_h}] [expr {$x1 + $pk_h}] $dy1] }
    S { set r [list [expr {$x0 - $pk_h}] $dy0 [expr {$x1 + $pk_h}] [expr {$y1 + $pk_h}]] }
  }
  set lv [[$pk_tech findLayer $ln] getRoutingLevel]
  foreach adj [list [expr {$lv - 1}] [expr {$lv + 1}]] {
    if {$adj < 2} continue
    set al [$pk_tech findRoutingLayer $adj]
    if {$al eq "NULL"} continue
    lappend pk_rects [concat [list [$al getName]] $r]
  }
}
set pk_have {}
foreach o [$pk_blk getObstructions] {
  set bx [$o getBBox]
  set key [list [[$bx getTechLayer] getName] [$bx xMin] [$bx yMin] [$bx xMax] [$bx yMax]]
  if {[lsearch -exact $pk_rects $key] >= 0} { lappend pk_have $o }
}
if {[llength $pk_have]} {
  foreach o $pk_have { odb::dbObstruction_destroy $o }
  puts "OT_PIN_KEEPOUT removed [llength $pk_have] of [llength $pk_rects]"
} else {
  foreach r $pk_rects {
    lassign $r ln a b c d
    odb::dbObstruction_create $pk_blk [$pk_tech findLayer $ln] $a $b $c $d
  }
  puts "OT_PIN_KEEPOUT created [llength $pk_rects]: $pk_rects"
}
