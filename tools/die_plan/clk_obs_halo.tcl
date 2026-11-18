# CLK-OBS-HALO 11-18 (COORD / FABLE-CLOSURE-STRATEGY 1530 lever 7, FABLE-FIX-HEAD-MESH): clock buffers keep a halo from the
# reserved M1-M7 route obstructions (clock-entry reservations, gen_phys reserved_sites_um kind die_clock_tree).
# HEAD hd_mesh mesh_w1: tap_balance seeds its delay chain at the tap port, which lies INSIDE the reserved site, so the
# legalizer leaves the cells on the edge of the placement blockage (3 padded sites E/W, none N/S).  clk_t41_tb0_d3 sat
# 0.162 um east of the obstruction and detail route died in iteration 2: [ERROR DRT-0255] Maze Route cannot find path of
# net clk_t41_tb0_tree (the kit lost 1 h 41 of route).  The same chain in mesh_pa had a cell directly under the obstruction.
#
# Every buffer / inverter that drives a CLOCK net and lies within OT_CLK_OBS_HALO_SITES sites (default 10 = 0.54 um: one
# site + the pin-access span of a BUFx4 output) in x, or within OT_CLK_OBS_HALO_ROWS rows (default 1) in y, of an M1 route
# obstruction at least one row tall moves to the nearest free legal site outside every halo.  Only these clock cells
# move; no other cell, no net, no blockage changes.  A cell with no free site in reach stays (OT_CLK_OBS_HALO WARN).
# OT_CLK_OBS_HALO=0 switches the pass off.  The planner is pure Tcl (test_clk_obs_halo.py).
namespace eval ::ot_clk_halo {
 # rect overlap with open edges (abutment is not overlap)
 proc hit {ax0 ay0 ax1 ay1 bx0 by0 bx1 by1} { expr {$ax0 < $bx1 && $bx0 < $ax1 && $ay0 < $by1 && $by0 < $ay1} }
 # is a cell bbox inside the halo of any obstruction: obs grown by hx in x and hy in y
 proc in_halo {x0 y0 x1 y1 obs hx hy} {
  foreach o $obs { lassign $o ox0 oy0 ox1 oy1
   if {[hit $x0 $y0 $x1 $y1 [expr {$ox0-$hx}] [expr {$oy0-$hy}] [expr {$ox1+$hx}] [expr {$oy1+$hy}]]} { return 1 } }
  return 0
 }
 # cells {name x0 y0 w h}; obs / blocks {x0 y0 x1 y1}; rows dict y -> {xmin xmax orient}; occ dict y -> {{x0 x1 name} ...}
 # -> {moves {{name x y orient} ...} stuck {name ...}}.  Candidates: the cell's row and up to maxrows rows above / below,
 # x on the site grid within maxsites sites; the nearest (Manhattan) free one wins, ties to the smaller y then x.
 proc plan {cells obs blocks rows occ hx hy site maxsites maxrows} {
  if {$site <= 0 || $hx < 0 || $hy < 0 || $maxsites < 1 || $maxrows < 0} { error "OT_CLK_OBS_HALO invalid site/halo/reach" }
  set ys [lsort -integer [dict keys $rows]]
  set moves {}; set stuck {}
  foreach c $cells {
   lassign $c name x0 y0 w h
   if {![in_halo $x0 $y0 [expr {$x0+$w}] [expr {$y0+$h}] $obs $hx $hy]} continue
   set i0 [lsearch -exact -integer $ys $y0]
   if {$i0 < 0} { lappend stuck $name; continue }
   set best {}; set bd -1
   for {set dr [expr {-$maxrows}]} {$dr <= $maxrows} {incr dr} {
    set i [expr {$i0 + $dr}]
    if {$i < 0 || $i >= [llength $ys]} continue
    set y [lindex $ys $i]
    lassign [dict get $rows $y] rx0 rx1 orient
    set busy [expr {[dict exists $occ $y] ? [dict get $occ $y] : {}}]
    for {set ds [expr {-$maxsites}]} {$ds <= $maxsites} {incr ds} {
     set x [expr {$x0 + $ds * $site}]
     set d [expr {abs($x - $x0) + abs($y - $y0)}]
     if {$bd >= 0 && $d >= $bd} continue
     if {$x < $rx0 || $x + $w > $rx1 || (($x - $rx0) % $site) != 0} continue
     if {[in_halo $x $y [expr {$x+$w}] [expr {$y+$h}] $obs $hx $hy]} continue
     set ok 1
     foreach b $blocks { lassign $b bx0 by0 bx1 by1; if {[hit $x $y [expr {$x+$w}] [expr {$y+$h}] $bx0 $by0 $bx1 $by1]} { set ok 0; break } }
     if {!$ok} continue
     foreach u $busy { lassign $u ux0 ux1 un; if {$un ne $name && $x < $ux1 && $ux0 < $x + $w} { set ok 0; break } }
     if {!$ok} continue
     set best [list $x $y $orient]; set bd $d
    }
   }
   if {$best eq {}} { lappend stuck $name; continue }
   lassign $best nx ny no
   # occupancy follows the move, so two halo cells never take the same site
   if {[dict exists $occ $y0]} { dict set occ $y0 [lmap u [dict get $occ $y0] { if {[lindex $u 2] eq $name} continue; set u }] }
   dict lappend occ $ny [list $nx [expr {$nx + $w}] $name]
   lappend moves [list $name $nx $ny $no]
  }
  return [dict create moves $moves stuck $stuck]
 }
 # OpenDB side: collect, plan, move.  Returns the number of cells moved.
 proc apply {} {
  if {[info exists ::env(OT_CLK_OBS_HALO)] && $::env(OT_CLK_OBS_HALO) eq "0"} { return 0 }
  set blk [ord::get_db_block]
  set rowsl [$blk getRows]
  if {![llength $rowsl]} { return 0 }
  set site [[[lindex $rowsl 0] getSite] getWidth]; set rh [[[lindex $rowsl 0] getSite] getHeight]
  set hs [expr {[info exists ::env(OT_CLK_OBS_HALO_SITES)] ? $::env(OT_CLK_OBS_HALO_SITES) : 10}]
  set hr [expr {[info exists ::env(OT_CLK_OBS_HALO_ROWS)] ? $::env(OT_CLK_OBS_HALO_ROWS) : 1}]
  set hx [expr {$hs * $site}]; set hy [expr {$hr * $rh}]
  # M1 route obstructions at least one row tall (reserved sites; PDN track guards are thinner and on upper layers)
  set obs {}
  foreach o [$blk getObstructions] {
   set b [$o getBBox]; set l [$b getTechLayer]
   if {$l eq "NULL" || [$l getName] ne "M1" || [$b yMax] - [$b yMin] < $rh} continue
   lappend obs [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]]
  }
  if {![llength $obs]} { return 0 }
  # clock buffers / inverters: non-sequential standard cells driving a CLOCK net
  set cells {}; set seen {}
  foreach net [$blk getNets] {
   if {[$net getSigType] ne "CLOCK"} continue
   foreach it [$net getITerms] {
    if {![$it isOutputSignal]} continue
    set inst [$it getInst]; set m [$inst getMaster]
    if {[$m isBlock] || [$m isSequential] || [$inst isFixed] || [dict exists $seen [$inst getName]]} continue
    dict set seen [$inst getName] 1
    set b [$inst getBBox]
    if {[in_halo [$b xMin] [$b yMin] [$b xMax] [$b yMax] $obs $hx $hy]} { lappend cells [list [$inst getName] [$b xMin] [$b yMin] [expr {[$b xMax]-[$b xMin]}] [expr {[$b yMax]-[$b yMin]}]] }
   }
  }
  if {![llength $cells]} { puts "OT_CLK_OBS_HALO 0 clock cells inside the halo ([llength $obs] M1 obstructions, halo $hs sites / $hr rows)"; return 0 }
  set rows {}
  foreach r $rowsl { set b [$r getBBox]; set y [$b yMin]
   if {[dict exists $rows $y]} { lassign [dict get $rows $y] a c o; dict set rows $y [list [expr {min($a,[$b xMin])}] [expr {max($c,[$b xMax])}] $o] } else { dict set rows $y [list [$b xMin] [$b xMax] [$r getOrient]] } }
  # occupancy of the rows in reach only
  set maxrows 6; set maxsites 400
  set want {}
  foreach c $cells { set y0 [lindex $c 2]; for {set k [expr {-$maxrows}]} {$k <= $maxrows} {incr k} { dict set want [expr {$y0 + $k * $rh}] 1 } }
  set occ {}
  foreach inst [$blk getInsts] {
   if {![$inst isPlaced]} continue
   set b [$inst getBBox]
   for {set y [$b yMin]} {$y < [$b yMax]} {incr y $rh} { if {[dict exists $want $y]} { dict lappend occ $y [list [$b xMin] [$b xMax] [$inst getName]] } }
  }
  set blocks {}
  foreach k [$blk getBlockages] { set b [$k getBBox]; lappend blocks [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]] }
  set res [plan $cells $obs $blocks $rows $occ $hx $hy $site $maxsites $maxrows]
  foreach mv [dict get $res moves] {
   lassign $mv name x y orient
   set inst [$blk findInst $name]
   $inst setOrient $orient
   $inst setLocation $x $y
  }
  puts "OT_CLK_OBS_HALO moved [llength [dict get $res moves]] of [llength $cells] clock cells out of the obstruction halo ($hs sites / $hr rows, [llength $obs] M1 obstructions): [lrange [lmap mv [dict get $res moves] {lindex $mv 0}] 0 11]"
  if {[llength [dict get $res stuck]]} { puts "OT_CLK_OBS_HALO WARN no free site in reach for [llength [dict get $res stuck]] clock cells: [lrange [dict get $res stuck] 0 11]" }
  return [llength [dict get $res moves]]
 }
}
