# S81 scoped forwarding-only HB bypass; original own-input/status stages retained.
# Hardened-leaf input hold stage (el1011-ds-misc 2026-10-11, PRE_GLOBAL_PLACE of route_leaf.sh INHOLD=1).  land8 a7247ecfa-f
# closed TT +325.95 / DRC 0 and missed FF hold by -24.5 ps on 2,023 input-pin -> capture-flop D pins (reg2reg -6.4).
# Deterministic fix (OWNER 10-10 "hold-only miss -> delay stage at inputs; no ECO loops") applied to EVERY data input
# uniformly: one dont_touch hold buffer (OT_INHOLD_MASTER, default HB4xp67) between each input port and its single
# capture-flop D pin.  Same insertion as io_flop_at_pins_inhold.tcl (cb2978cc5) without the pin anchoring.
set ot_ih_master [expr {[info exists ::env(OT_INHOLD_MASTER)] ? $::env(OT_INHOLD_MASTER) : "HB4xp67_ASAP7_75t_R"}]
set ot_ih_blk [ord::get_db_block]
set ot_ih_m [[ord::get_db] findMaster $ot_ih_master]
if {$ot_ih_m eq "NULL"} { error "INHOLD: $ot_ih_master missing" }
# [vm8 r11] strong driver after the hold cell (OT_INHOLD_DRV, e.g. BUFx4f_ASAP7_75t_R; default "" = off, so other users of this hook are unchanged): r9 (4e6ad7d42) left the
# HB4 hold cell -- a deliberately slow, weak delay cell -- driving the whole pin -> capture-flop wire (hfd_vm_nw_w_t4
# TT -38.17: d2_0[30] -> ot_inhold_00233/Y 432.9 ps -> w2e_658/D; the same input paths were +297 ps without the stage).
# Now port -> HB4 -> BUF sit together at the pin: the HB4 sees one short local load (its intrinsic delay is the hold
# delay this stage exists to add), the BUF drives the long wire and stays resizable; the HB4->BUF net is dont_touch so
# the resizer cannot unbuffer the pair.  Both cells are FIRM through global placement (timing-driven GPL otherwise
# drags the pair toward the flop and the dont_touch port net becomes the long wire) and are returned to PLACED for
# DPL by leaf_inhold_release.tcl (PRE_DETAIL_PLACE; list in RESULTS_DIR/ot_inhold_firm.txt).
set ot_ih_drv [expr {[info exists ::env(OT_INHOLD_DRV)] ? $::env(OT_INHOLD_DRV) : ""}]
set ot_ih_dm "NULL"
if {$ot_ih_drv ne ""} {
  set ot_ih_dm [[ord::get_db] findMaster $ot_ih_drv]
  if {$ot_ih_dm eq "NULL"} { error "INHOLD: $ot_ih_drv missing" }
}
set ot_ih_firm {}
set ot_ih_bypass 0
set ot_ih_n 0; set ot_ih_skip 0; set ot_ih_pnets {}; set ot_ih_dnets {}
foreach bt [$ot_ih_blk getBTerms] {
  if {[$bt getIoType] ne "INPUT"} continue
  set net [$bt getNet]; if {$net eq "NULL"} continue
  if {[$net getSigType] ne "SIGNAL"} { incr ot_ih_skip; continue }
  set its [$net getITerms]
  if {[llength $its] != 1} { incr ot_ih_skip; continue }
  set d [lindex $its 0]; set ff [$d getInst]
  if {![string match "DFF*" [[$ff getMaster] getName]] || [[$d getMTerm] getName] ne "D"} { incr ot_ih_skip; continue }
  set name [format "ot_inhold_%05d" $ot_ih_n]; set nn [format "ot_inhold_n%05d" $ot_ih_n]
  set forwarding 0
  if {[regexp {^li\[([0-9]+)\]$} [$bt getName] -> bit] && $bit>=276} {set forwarding 1}
  if {[regexp {^ci\[([0-9]+)\]$} [$bt getName] -> bit] && $bit<636} {set forwarding 1}
  if {$forwarding} {
    if {$ot_ih_dm eq "NULL"} {error "S81_FORWARD_HB requires strong input driver"}
    set cell [odb::dbInst_create $ot_ih_blk $ot_ih_dm [format "ot_ihdrv_%05d" $ot_ih_n]]
    set n2 [odb::dbNet_create $ot_ih_blk $nn]
    $d disconnect
    [$cell findITerm A] connect $net
    [$cell findITerm Y] connect $n2
    $d connect $n2
    set drv ""
    incr ot_ih_bypass
  } else {
  set cell [odb::dbInst_create $ot_ih_blk $ot_ih_m $name]
  set n2 [odb::dbNet_create $ot_ih_blk $nn]
  $d disconnect
  [$cell findITerm A] connect $net
  [$cell findITerm Y] connect $n2
  if {$ot_ih_dm ne "NULL"} {
    set drv [odb::dbInst_create $ot_ih_blk $ot_ih_dm [format "ot_ihdrv_%05d" $ot_ih_n]]
    set n3 [odb::dbNet_create $ot_ih_blk [format "ot_ihdrv_n%05d" $ot_ih_n]]
    [$drv findITerm A] connect $n2
    [$drv findITerm Y] connect $n3
    $d connect $n3
    lappend ot_ih_dnets $n2
  } else {
    set drv ""
    $d connect $n2
  }
  }
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
  $cell setOrient R0; $cell setLocation $x $y
  if {$drv ne ""} {
    $cell setPlacementStatus FIRM; lappend ot_ih_firm [$cell getName]
    $drv setOrient R0; $drv setLocation $x $y; $drv setPlacementStatus FIRM; lappend ot_ih_firm [$drv getName]
  } else {
    $cell setPlacementStatus FIRM; lappend ot_ih_firm [$cell getName]
  }
  if {!$forwarding} {lappend ot_ih_pnets $net}
  incr ot_ih_n
}
if {$ot_ih_n > 0} {
  set_dont_touch [get_cells ot_inhold_*]
  foreach pn $ot_ih_pnets { $pn setDoNotTouch 1 }
  foreach dn $ot_ih_dnets { $dn setDoNotTouch 1 }
}
if {[info exists ::env(RESULTS_DIR)]} {
  set fh [open $::env(RESULTS_DIR)/ot_inhold_firm.txt w]; puts $fh [join $ot_ih_firm "\n"]; close $fh
}
puts "INHOLD: $ot_ih_n input hold cells ($ot_ih_master, dont_touch; driver '$ot_ih_drv', [llength $ot_ih_firm] FIRM for GPL), $ot_ih_skip inputs skipped (clock / reset / multi-sink / non-DFF)"

puts "S81_FORWARD_HB inputs: $ot_ih_bypass forwarding HB bypasses; strong BUF retained; own-input/status HB unchanged"
