# DIE-HBM-89-SPB2F q_spb2 vF (COORD 19:0x ruling item 2): no lone weak cell drives a station hop.
# Measured on vE routed (signoff/tt/sta.log): worst path ft_L1280x6_o_2 QN -> BUFx3 -> INVx1 _1297_ driving the 340 um hop
# alone, 554 ps, slew 445; 4,623 of 16,056 TT slew pins are station D pins.  Rule here: every signal net whose pin bbox
# half-perimeter is >= OT_HOP_DRIVE_UM (default 150 um) and whose driver is a weak INV/BUF (INVx1-3, BUFx2-4f) gets that
# driver swapped to the same-function strong cell (INVx6 / BUFx6f, same row height, legalized by the next detailed
# placement).  Flop-driven long nets are only counted (their footprint is FIRM in an explicit FT site; repair_design
# buffers them).  Clock nets are untouched.  0 PIN CYCLES, netlist function unchanged (LEC-neutral cell swap).
# Sourced as a step hook (PRE_RESIZE / POST_RESIZE / PRE_GLOBAL_ROUTE wrappers).
proc ot_hop_drive {tag} {
  set lim [expr {[info exists ::env(OT_HOP_DRIVE_UM)] && $::env(OT_HOP_DRIVE_UM) ne "" ? $::env(OT_HOP_DRIVE_UM) : 150.0}]
  set db [ord::get_db]; set blk [[$db getChip] getBlock]; set dbu [$blk getDefUnits]
  set map {}
  foreach {weak strong} {INVx1 INVx6 INVx2 INVx6 INVx3 INVx6 BUFx2 BUFx6f BUFx3 BUFx6f BUFx4 BUFx6f BUFx4f BUFx6f} {
    set m [$db findMaster ${strong}_ASAP7_75t_R]
    if {$m eq "NULL" || $m eq ""} { error "hop_drive: master ${strong}_ASAP7_75t_R missing" }
    dict set map ${weak}_ASAP7_75t_R $m
  }
  set nsw 0; set nff 0; set nlong 0; set seen {}
  foreach net [$blk getNets] {
    if {[$net getSigType] ne "SIGNAL"} continue
    set its [$net getITerms]
    if {[llength $its] < 2 && [llength [$net getBTerms]] == 0} continue
    set drv ""
    set x0 1e18; set y0 1e18; set x1 -1e18; set y1 -1e18
    foreach it $its {
      if {[$it isOutputSignal]} { set drv $it }
      set inst [$it getInst]
      set b [$inst getBBox]
      set cx [expr {([$b xMin] + [$b xMax]) / 2}]; set cy [expr {([$b yMin] + [$b yMax]) / 2}]
      if {$cx < $x0} { set x0 $cx }; if {$cx > $x1} { set x1 $cx }
      if {$cy < $y0} { set y0 $cy }; if {$cy > $y1} { set y1 $cy }
    }
    foreach bt [$net getBTerms] {
      set b [$bt getBBox]
      set cx [expr {([$b xMin] + [$b xMax]) / 2}]; set cy [expr {([$b yMin] + [$b yMax]) / 2}]
      if {$cx < $x0} { set x0 $cx }; if {$cx > $x1} { set x1 $cx }
      if {$cy < $y0} { set y0 $cy }; if {$cy > $y1} { set y1 $cy }
    }
    if {$drv eq ""} continue
    if {($x1 - $x0) + ($y1 - $y0) < $lim * $dbu} continue
    incr nlong
    set inst [$drv getInst]; set mn [[$inst getMaster] getName]
    if {[string match "*DFF*" $mn]} { incr nff; continue }
    if {![dict exists $map $mn]} continue
    if {[dict exists $seen [$inst getName]]} continue
    dict set seen [$inst getName] 1
    if {[$inst getPlacementStatus] eq "FIRM" || [$inst getPlacementStatus] eq "LOCKED"} continue
    $inst swapMaster [dict get $map $mn]
    incr nsw
  }
  puts "OT_HOP_DRIVE $tag: nets with hpwl >= $lim um: $nlong; weak INV/BUF drivers upsized: $nsw; flop-driven (counted only): $nff"
}
