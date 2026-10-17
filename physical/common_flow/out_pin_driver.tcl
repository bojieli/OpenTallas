# Opt-in strong output-pin driver (S-ELEM ENGRAM-LKP 2026-10-16, S81 relay/station electrical reach).
# Use from a ref_tile spec:  "pin_hook_before_flops": ["physical/common_flow/out_pin_driver.tcl"],
#                            "orfs_vars": {"OT_OUT_DRV": "BUFx8_ASAP7_75t_R"}
# Why: H-REACH's native electrical replay of the CLOSED stnv566 view (claude/sdie-reach-1016 1f9ab4788) fails the receiver's
# first input cell (HB2xp67, recipe-2 input hold) at 225 um: 298 ps > 260 max transition.  The sender's out pin there,
# and in the closed s81_rly_536_* / s81fill_hstn* views (outhold false), is a BUFx2 (hold-repair buffer) or the flop
# itself.  ASAP7 TT driver-end rise transition at ~0.167 fF/um of die wire: BUFx2 170 ps @225 um / 335 ps @450 um,
# BUFx4f 88 / 171, BUFx8 50 / 94, BUFx12f 36 / 67 (before wire RC).
# What: every flop-driven OUTPUT port (driver a DFF, or <= 3 BUF/INV/HB back to one) gets ONE OT_OUT_DRV cell between
# its net and the port, FIRM at the pin and dont_touch (repair_design / hold repair cannot downsize it or put a weak
# cell behind the port).  It is appended to RESULTS_DIR/ot_inhold_firm.txt, so the kit's PRE_DETAIL_PLACE
# leaf_inhold_release.tcl returns it to PLACED for DPL like the hold stages.  Sourced by the recipe-2 pin hook after the
# hold stages and BEFORE io_flop_at_pins.tcl, which then traces each launch flop THROUGH it (OT_OFLOP_HOPS) to the pin.
# Function and cycles unchanged (one non-inverting buffer).  Default off: without OT_OUT_DRV this file does nothing.
if {![info exists ::env(OT_OUT_DRV)] || $::env(OT_OUT_DRV) eq ""} {
  puts "OUT_PIN_DRIVER: OT_OUT_DRV unset, nothing inserted"
} else {
  set ot_od_blk [ord::get_db_block]
  set ot_od_m [[ord::get_db] findMaster $::env(OT_OUT_DRV)]
  if {$ot_od_m eq "NULL"} { error "OUT_PIN_DRIVER: master $::env(OT_OUT_DRV) missing" }
  if {![string match "BUF*" [$ot_od_m getName]]} { error "OUT_PIN_DRIVER: OT_OUT_DRV must be a non-inverting BUF" }
  set ot_od_ca [$ot_od_blk getCoreArea]
  set ot_od_firm {}; set ot_od_n 0; set ot_od_skip 0
  foreach bt [$ot_od_blk getBTerms] {
    if {[$bt getIoType] ne "OUTPUT"} continue
    set net [$bt getNet]; if {$net eq "NULL" || [$net getSigType] ne "SIGNAL"} continue
    set ok 0; set cn $net
    for {set k 0} {$k < 4} {incr k} {
      set dv ""
      foreach it [$cn getITerms] { if {[$it isOutputSignal]} { set dv $it; break } }
      if {$dv eq ""} break
      set di [$dv getInst]; set dm [[$di getMaster] getName]
      if {[string match "DFF*" $dm]} { set ok 1; break }
      if {![regexp {^(BUF|INV|HB)} $dm]} break
      set cn [[$di findITerm A] getNet]; if {$cn eq "NULL"} break
    }
    if {!$ok} { incr ot_od_skip; continue }
    set x 0; set y 0
    foreach bp [$bt getBPins] { foreach bx [$bp getBoxes] {
      set x [expr {([$bx xMin] + [$bx xMax]) / 2}]; set y [expr {([$bx yMin] + [$bx yMax]) / 2}]; break }; break }
    set x [expr {max([$ot_od_ca xMin], min($x, [$ot_od_ca xMax] - [$ot_od_m getWidth]))}]
    set y [expr {max([$ot_od_ca yMin], min($y, [$ot_od_ca yMax] - [$ot_od_m getHeight]))}]
    set pn [odb::dbNet_create $ot_od_blk [format "ot_outdrv_p%05d" $ot_od_n]]
    $bt disconnect
    $bt connect $pn
    set nm [format "ot_outdrv_%05d" $ot_od_n]
    set i [odb::dbInst_create $ot_od_blk $ot_od_m $nm]
    [$i findITerm A] connect $net
    [$i findITerm Y] connect $pn
    $i setOrient R0
    $i setLocation $x $y
    $i setPlacementStatus FIRM
    lappend ot_od_firm $nm
    $pn setDoNotTouch 1
    incr ot_od_n
  }
  if {$ot_od_n > 0} { set_dont_touch [get_cells ot_outdrv_*] }
  if {[info exists ::env(RESULTS_DIR)]} {
    set fh [open $::env(RESULTS_DIR)/ot_inhold_firm.txt a]; if {[llength $ot_od_firm]} { puts $fh [join $ot_od_firm "\n"] }; close $fh
  }
  puts "OUT_PIN_DRIVER: $ot_od_n output ports driven by [$ot_od_m getName] FIRM at the pin (dont_touch), $ot_od_skip outputs skipped (not flop-driven)"
}
