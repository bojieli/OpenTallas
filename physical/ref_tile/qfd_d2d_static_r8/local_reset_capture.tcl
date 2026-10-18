# r8 (Q-LINK 1815): place BOTH kept first reset-capture pairs (por_n -> u_por_region.s0/s1, rst_n -> u_reset_regions.s0/s1) at their E-face ports (r7f anchored only por_n: routed rst_n capture 239.9 = HB2 pad on an 11 fF long wire + 49 ps wire to s0 RESETN). The ck tree is the balanced spine, so anchors no longer skew a TritonCTS tree (r6).
# No added cells, nets, cycles or timing exceptions. Regional stages follow loads.
set rb [ord::get_db_block]
set ru [[ord::get_db_tech] getDbUnitsPerMicron]
set reset_owned {}
foreach {port pattern} {por_n {u_core.u_por_region.s[01]*} rst_n {u_core.u_reset_regions.s[01]*}} {
  set bt [$rb findBTerm $port]
  if {$bt eq "NULL"} {error "RESET_CAPTURE missing $port"}
  set box [$bt getBBox];set px [expr {([$box xMin]+[$box xMax])/2.0}];set py [expr {([$box yMin]+[$box yMax])/2.0}]
  set matches {}
  foreach inst [$rb getInsts] {
    if {[string match $pattern [$inst getName]] && [string match *DFF* [[$inst getMaster] getName]]} {lappend matches $inst}
  }
  if {[llength $matches] != 2} {error "RESET_CAPTURE $port expected exactly 2 kept captures, got [llength $matches]"}
  foreach ff $matches {
    set score Inf;set best {};set width [[$ff getMaster] getWidth];set height [[$ff getMaster] getHeight]
    foreach row [$rb getRows] {
      set b [$row getBBox];set ry [$b yMin];set rx [$b xMin];set ex [$b xMax];set pitch [$row getSpacing]
      if {$height != [$b yMax]-$ry || $pitch <= 0} continue
      set target [expr {$px-8.64*$ru-$width/2.0}]
      set x [expr {max($rx,min($ex-$width,$rx+round(($target-$rx)/$pitch)*$pitch))}]
      set cost [expr {abs($x+$width/2.0-$px)+abs($ry+$height/2.0-$py)}]
      if {$cost<$score} {set score $cost;set best [list $x $ry [$row getOrient]]}
    }
    if {$best eq ""} {error "RESET_CAPTURE no legal row"}
    lassign $best x y orient;$ff setOrient $orient;$ff setLocation $x $y;$ff setPlacementStatus FIRM
    lappend reset_owned [$ff getName]
  }
}
source /src/physical/common_flow/anchor_row_packing.tcl
ot_anchor_pack::repair $rb $reset_owned
foreach name $reset_owned {puts "RESET_CAPTURE $name [[$rb findInst $name] getLocation]"}
