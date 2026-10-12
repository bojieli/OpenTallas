# Hardened-leaf input hold stage (el1011-ds-misc 2026-10-11, PRE_GLOBAL_PLACE of route_leaf.sh INHOLD=1).  land8 a7247ecfa-f
# closed TT +325.95 / DRC 0 and missed FF hold by -24.5 ps on 2,023 input-pin -> capture-flop D pins (reg2reg -6.4).
# Deterministic fix (OWNER 10-10 "hold-only miss -> delay stage at inputs; no ECO loops") applied to EVERY data input
# uniformly: one dont_touch hold buffer (OT_INHOLD_MASTER, default HB4xp67) between each input port and its single
# capture-flop D pin.  Same insertion as io_flop_at_pins_inhold.tcl (cb2978cc5) without the pin anchoring.
set ot_ih_master [expr {[info exists ::env(OT_INHOLD_MASTER)] ? $::env(OT_INHOLD_MASTER) : "HB4xp67_ASAP7_75t_R"}]
set ot_ih_blk [ord::get_db_block]
set ot_ih_m [[ord::get_db] findMaster $ot_ih_master]
if {$ot_ih_m eq "NULL"} { error "INHOLD: $ot_ih_master missing" }
set ot_ih_n 0; set ot_ih_skip 0; set ot_ih_pnets {}
foreach bt [$ot_ih_blk getBTerms] {
  if {[$bt getIoType] ne "INPUT"} continue
  set net [$bt getNet]; if {$net eq "NULL"} continue
  if {[$net getSigType] ne "SIGNAL"} { incr ot_ih_skip; continue }
  set its [$net getITerms]
  if {[llength $its] != 1} { incr ot_ih_skip; continue }
  set d [lindex $its 0]; set ff [$d getInst]
  if {![string match "DFF*" [[$ff getMaster] getName]] || [[$d getMTerm] getName] ne "D"} { incr ot_ih_skip; continue }
  set name [format "ot_inhold_%05d" $ot_ih_n]; set nn [format "ot_inhold_n%05d" $ot_ih_n]
  set cell [odb::dbInst_create $ot_ih_blk $ot_ih_m $name]
  set n2 [odb::dbNet_create $ot_ih_blk $nn]
  $d disconnect
  [$cell findITerm A] connect $net
  [$cell findITerm Y] connect $n2
  $d connect $n2
  # [vm8 r9] seed the hold cell AT its input pin (clamped into the core), not at the capture flop: GPL's timing-driven
  # repair_design otherwise sees a long port -> hold-cell wire whose only load is dont_touch and aborts with RSZ-3006
  # "Failed to insert buffer before loads" (hbm_vm8st8_nwwt4 cal: e2w__t[9], tile 500 um tall).  The port net (one
  # load, the dont_touch hold cell) is dont_touch as well: a repeater on it would also change the hold delay this
  # stage exists to add.  The flop side (hold cell -> D) stays fully repairable.
  lassign [$ff getLocation] x y
  foreach bp [$bt getBPins] { foreach bx [$bp getBoxes] {
    set x [expr {([$bx xMin] + [$bx xMax]) / 2}]; set y [expr {([$bx yMin] + [$bx yMax]) / 2}]; break } ; break }
  set ca [$ot_ih_blk getCoreArea]
  set x [expr {max([$ca xMin], min($x, [$ca xMax] - [$ot_ih_m getWidth]))}]
  set y [expr {max([$ca yMin], min($y, [$ca yMax] - [$ot_ih_m getHeight]))}]
  $cell setOrient R0; $cell setLocation $x $y; $cell setPlacementStatus PLACED
  lappend ot_ih_pnets $net
  incr ot_ih_n
}
if {$ot_ih_n > 0} {
  set_dont_touch [get_cells ot_inhold_*]
  foreach pn $ot_ih_pnets { $pn setDoNotTouch 1 }
}
puts "INHOLD: $ot_ih_n input hold cells ($ot_ih_master, dont_touch), $ot_ih_skip inputs skipped (clock / reset / multi-sink / non-DFF)"
