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
# Pad sized from the measured hold need (el1014-root-recipe2, 2026-10-14; ref_tile recipe 2 / spec "hold_pad"): the
# pad above is the default (recipe 2: HB2xp67); ports whose name matches OT_HOLD_PAD_STRONG_RE take
# OT_HOLD_PAD_STRONG_MASTER (default HB4xp67) instead -- only where a routed FF report measured the HB2 pad short.  An
# HB4 pad on every pin costs ~120 ps TT of native launch / capture budget (Qwen cache R2 239.6 ps > 220; FF output hold
# +36 ps = overpadded; the HB2 run: +15.3).  Unset = every port takes the default pad (unchanged behaviour).
set ot_ih_sre [expr {[info exists ::env(OT_HOLD_PAD_STRONG_RE)] ? $::env(OT_HOLD_PAD_STRONG_RE) : ""}]
set ot_ih_sm "NULL"
if {$ot_ih_sre ne ""} {
  set ot_ih_sm [[ord::get_db] findMaster [expr {([info exists ::env(OT_HOLD_PAD_STRONG_MASTER)] && $::env(OT_HOLD_PAD_STRONG_MASTER) ne "") ? $::env(OT_HOLD_PAD_STRONG_MASTER) : "HB4xp67_ASAP7_75t_R"}]]
  if {$ot_ih_sm eq "NULL"} { error "INHOLD: strong pad master missing" }
}
set ot_ih_ns 0
set ot_ih_firm {}
set ot_ih_n 0; set ot_ih_skip 0; set ot_ih_pnets {}; set ot_ih_dnets {}
foreach bt [$ot_ih_blk getBTerms] {
  if {[$bt getIoType] ne "INPUT"} continue
  set net [$bt getNet]; if {$net eq "NULL"} continue
  if {[$net getSigType] ne "SIGNAL"} { incr ot_ih_skip; continue }
  # Output-register splitting can create several identical D captures. Insert
  # one pad before that fanout, rather than silently dropping input hold repair.
  # A reset synchronizer's D may share the port with async-reset pins; leave
  # those reset loads on the original net, outside the data delay chain.
  set captures {}; set other_load 0
  foreach it [$net getITerms] {
    if {![$it isInputSignal]} { set other_load 1; break }
    set inst [$it getInst]; set master [[$inst getMaster] getName]
    if {![string match "DFF*" $master] && ![string match "ASYNC_DFF*" $master]} { set other_load 1; break }
    if {[[$it getMTerm] getName] eq "D"} { lappend captures $it }
  }
  if {$other_load || ![llength $captures]} { incr ot_ih_skip; continue }
  set ff [[lindex $captures 0] getInst]
  set name [format "ot_inhold_%05d" $ot_ih_n]; set nn [format "ot_inhold_n%05d" $ot_ih_n]
  set pm $ot_ih_m
  if {$ot_ih_sm ne "NULL" && [regexp -- $ot_ih_sre [$bt getName]]} { set pm $ot_ih_sm; incr ot_ih_ns }
  set cell [odb::dbInst_create $ot_ih_blk $pm $name]
  set n2 [odb::dbNet_create $ot_ih_blk $nn]
  foreach d $captures { $d disconnect }
  [$cell findITerm A] connect $net
  [$cell findITerm Y] connect $n2
  if {$ot_ih_dm ne "NULL"} {
    set drv [odb::dbInst_create $ot_ih_blk $ot_ih_dm [format "ot_ihdrv_%05d" $ot_ih_n]]
    set n3 [odb::dbNet_create $ot_ih_blk [format "ot_ihdrv_n%05d" $ot_ih_n]]
    [$drv findITerm A] connect $n2
    [$drv findITerm Y] connect $n3
    foreach d $captures { $d connect $n3 }
    lappend ot_ih_dnets $n2
  } else {
    set drv ""
    foreach d $captures { $d connect $n2 }
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
  set x [expr {max([$ca xMin], min($x, [$ca xMax] - [$pm getWidth]))}]
  set y [expr {max([$ca yMin], min($y, [$ca yMax] - [$pm getHeight]))}]
  $cell setOrient R0
  if {[[$cell getMaster] isBlock]} {error {standard cell placement refuses BLOCK}}
  $cell setLocation $x $y
  if {$drv ne ""} {
    $cell setPlacementStatus FIRM; lappend ot_ih_firm [$cell getName]
    $drv setOrient R0
    if {[[$drv getMaster] isBlock]} {error {standard cell placement refuses BLOCK}}
    $drv setLocation $x $y; $drv setPlacementStatus FIRM; lappend ot_ih_firm [$drv getName]
  } else {
    $cell setPlacementStatus PLACED
  }
  lappend ot_ih_pnets $net
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
puts "INHOLD: $ot_ih_n input hold cells ($ot_ih_master; $ot_ih_ns strong pads by OT_HOLD_PAD_STRONG_RE, dont_touch; driver '$ot_ih_drv', [llength $ot_ih_firm] FIRM for GPL), $ot_ih_skip inputs skipped (clock / reset-only / non-DFF)"
