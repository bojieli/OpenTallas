# PRE_DETAIL_PLACE hook (HNX-UNITS/VM safe4, 2026-10-20): face-root pin flops grouped beside their face clock entry.
# Why: safe3 gates 1-3 (10-20) failed CTS on root clk_e only, pin-flop spread 85.2..102.4 ps TT (> 80) under three
# CTS clustering variants.  The placed sinks (3_place.odb, gate3) show 95% of the 1,133 clk_e pin flops at x >= 348
# (the E end of the one full-width band) and a 3% tail pulled by timing-driven GPL to x 127..300 (rr1 / eg output
# registers); clk_w is worse (sinks over x 2..459, 300 of them at x 275..350).  One face tree over a 21.6 um x ~350 um
# strip with a far tail is the unbalanced case; the face clock entry must sit beside its register mass.
# What: after GPL / resize, every sink of a face root (clk_e, clk_w) outside its face window (the band end beside the
# face pin, OT_FW_UM wide, default 125 um) moves onto the window edge at its own y; DPL then legalises it.  Placement
# only: netlist, cycles and schedule unchanged.  The N / S roots are centre-fed and passed (28..69 ps): untouched.
set fw_blk [ord::get_db_block]
set fw_dbu [$fw_blk getDbUnitsPerMicron]
set fw_core [$fw_blk getCoreArea]
set fw_x0 [$fw_core xMin]; set fw_x1 [$fw_core xMax]
set fw_w [expr {round(([info exists ::env(OT_FW_UM)] && $::env(OT_FW_UM) ne "" ? $::env(OT_FW_UM) : 125.0) * $fw_dbu)}]
set fw_tot 0
foreach {fw_ck fw_side} {clk_e E clk_w W} {
  set fw_net [$fw_blk findNet $fw_ck]
  if {$fw_net eq "NULL" || $fw_net eq ""} { error "OT_FACE_WINDOW: no net $fw_ck" }
  set fw_n 0; set fw_moved 0
  foreach it [$fw_net getITerms] {
    set i [$it getInst]
    if {[$i isFixed] || [[$i getMaster] isBlock]} continue
    incr fw_n
    set bb [$i getBBox]
    set w [expr {[$bb xMax] - [$bb xMin]}]
    lassign [$i getLocation] x y
    if {$fw_side eq "E"} {
      set lo [expr {$fw_x1 - $fw_w}]
      if {$x >= $lo} continue
      set nx $lo
    } else {
      set hi [expr {$fw_x0 + $fw_w - $w}]
      if {$x <= $hi} continue
      set nx $hi
    }
    $i setLocation $nx $y
    incr fw_moved
  }
  puts "OT_FACE_WINDOW $fw_ck face $fw_side sinks $fw_n moved $fw_moved window [expr {$fw_w / double($fw_dbu)}] um"
  if {$fw_n == 0} { error "OT_FACE_WINDOW: root $fw_ck has no movable sinks" }
  incr fw_tot $fw_moved
}
puts "OT_FACE_WINDOW done: $fw_tot face-root pin flops moved into their face windows (DPL legalises next)"
