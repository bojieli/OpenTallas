# Hardened-leaf INPUT + OUTPUT hold stages (el1011 [hc-cpin] 2026-10-12, PRE_GLOBAL_PLACE of ref_tile spec 'outhold').
# s81hc_cpin_ref-v1-89a4bcc13 routed TT +117.89 / FF -7.14 / DRC 0; R2R +40.43; the FF misses are ALL boundary pin flops:
#   R2O: pin flop Q -> INV -> BUF -> port = 71 ps vs out min (L_min + 50 hold skew + 25 unc) -> -7.14 (n_y / n_rs_d ports)
#   I2R: port -> BUF -> single capture pin flop D = 48 ps -> -2.42 (y_s -> n_y, n_rq_row -> rq_row)
# The loop's post-route hold ECO added 5,387 cells and reached only -1.61.  Deterministic fix (OWNER 10-10 "hold-only
# miss -> delay stage at the boundary; no ECO loops"), applied uniformly:
#   INPUT  : leaf_inhold.tcl unchanged (port -> HB4 -> BUF -> capture flop D, pair FIRM at the pin), when OT_IOHOLD_IN=1.
#   OUTPUT : flop-driven output (directly or via <= 3 BUF/INV) -> lead BUF -> HB4 -> BUF -> port, all three FIRM at the
#            pin (qwen ctlm_hold_stages amh2 pattern: the long flop -> pin wire ends on a resizable lead BUF, so GPL's
#            repair_design never sees a dont_touch load (RSZ-3006); only the HB4 and its short input net are dont_touch).
# FIRM cells are appended to RESULTS_DIR/ot_inhold_firm.txt; leaf_inhold_release.tcl (PRE_DETAIL_PLACE) returns them to
# PLACED for DPL.  No procs: ORFS sources step hooks inside a proc.
# OT_OUTHOLD_FREE=1 (opt-in, Q-DVM 2026-10-15, qfd_xcst_*_m5): the three output-stage cells are SEEDED at the pin but left
# PLACED (not FIRM, not in the release list), so timing-driven GPL spreads them between the launch flop and the pin.
# Why: on a 52.68 um face with 516 M5-only output pins, FIRM BUF+HB+BUF stacks at every pin packed the y<6 um band
# (m5a/m5b GRT-0116, 2,344 of 4,442 hot-region refs were ot_outhold nets); dropping the pads instead (m5c) let hold
# repair build up to 6 x BUFx2 chains on the launch path (native launch 224.7..235.5 > 220).  The hold cell stays
# dont_touch, so the hold delay is still one deterministic pad; only its location is free.
set ot_oh_free [expr {[info exists ::env(OT_OUTHOLD_FREE)] && $::env(OT_OUTHOLD_FREE) eq "1"}]
if {[info exists ::env(OT_IOHOLD_IN)] && $::env(OT_IOHOLD_IN)} {
  source /src/physical/dsrom_window_source/leaf_inhold.tcl
}
set ot_oh_blk [ord::get_db_block]
# OT_OUTHOLD_MASTER (ref_tile hold_pad.out_cell): a separate output pad; default the input pad (unchanged kits)
set ot_oh_hb [[ord::get_db] findMaster [expr {([info exists ::env(OT_OUTHOLD_MASTER)] && $::env(OT_OUTHOLD_MASTER) ne "") ? $::env(OT_OUTHOLD_MASTER) : ([info exists ::env(OT_INHOLD_MASTER)] ? $::env(OT_INHOLD_MASTER) : "HB4xp67_ASAP7_75t_R")}]]
set ot_oh_bf [[ord::get_db] findMaster [expr {([info exists ::env(OT_INHOLD_DRV)] && $::env(OT_INHOLD_DRV) ne "") ? $::env(OT_INHOLD_DRV) : "BUFx4f_ASAP7_75t_R"}]]
if {$ot_oh_hb eq "NULL" || $ot_oh_bf eq "NULL"} { error "OUTHOLD: master missing" }
# per-port strong pad (el1014-root-recipe2; see leaf_inhold.tcl): OT_HOLD_PAD_STRONG_RE ports take
# OT_HOLD_PAD_STRONG_MASTER (default HB4xp67), every other output the default pad above (recipe 2: HB2xp67)
set ot_oh_sre [expr {[info exists ::env(OT_HOLD_PAD_STRONG_RE)] ? $::env(OT_HOLD_PAD_STRONG_RE) : ""}]
set ot_oh_shb "NULL"
if {$ot_oh_sre ne ""} {
  set ot_oh_shb [[ord::get_db] findMaster [expr {([info exists ::env(OT_HOLD_PAD_STRONG_MASTER)] && $::env(OT_HOLD_PAD_STRONG_MASTER) ne "") ? $::env(OT_HOLD_PAD_STRONG_MASTER) : "HB4xp67_ASAP7_75t_R"}]]
  if {$ot_oh_shb eq "NULL"} { error "OUTHOLD: strong pad master missing" }
}
set ot_oh_ns 0
set ot_oh_ca [$ot_oh_blk getCoreArea]
set ot_oh_firm {}; set ot_oh_dt {}; set ot_oh_n 0; set ot_oh_skip 0
foreach bt [$ot_oh_blk getBTerms] {
  if {[$bt getIoType] ne "OUTPUT"} continue
  set net [$bt getNet]; if {$net eq "NULL" || [$net getSigType] ne "SIGNAL"} continue
  # flop-driven: driver is a DFF, or a BUF/INV chain (<= 3) back to a DFF
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
  if {!$ok} { incr ot_oh_skip; continue }
  set x 0; set y 0
  foreach bp [$bt getBPins] { foreach bx [$bp getBoxes] {
    set x [expr {([$bx xMin] + [$bx xMax]) / 2}]; set y [expr {([$bx yMin] + [$bx yMax]) / 2}]; break }; break }
  set x [expr {max([$ot_oh_ca xMin], min($x, [$ot_oh_ca xMax] - [$ot_oh_hb getWidth]))}]
  set y [expr {max([$ot_oh_ca yMin], min($y, [$ot_oh_ca yMax] - [$ot_oh_hb getHeight]))}]
  set hb $ot_oh_hb
  if {$ot_oh_shb ne "NULL" && [regexp -- $ot_oh_sre [$bt getName]]} { set hb $ot_oh_shb; incr ot_oh_ns }
  set pn [odb::dbNet_create $ot_oh_blk [format "ot_outhold_p%05d" $ot_oh_n]]
  $bt disconnect
  $bt connect $pn
  set cur $net; set k 0
  foreach m [list $ot_oh_bf $hb $ot_oh_bf] {
    set hold [expr {$m eq $hb}]
    set nm [format "%s_%05d_%d" [expr {$hold ? "ot_outhold" : "ot_ohdrv"}] $ot_oh_n $k]
    set i [odb::dbInst_create $ot_oh_blk $m $nm]
    [$i findITerm A] connect $cur
    if {$k == 2} {
      [$i findITerm Y] connect $pn
    } else {
      set n2 [odb::dbNet_create $ot_oh_blk [format "ot_outhold_n%05d_%d" $ot_oh_n $k]]
      [$i findITerm Y] connect $n2
      set cur $n2
    }
    if {$hold} { lappend ot_oh_dt [[$i findITerm A] getNet] }
    $i setOrient R0
    if {[[$i getMaster] isBlock]} {error {standard cell placement refuses BLOCK}}
    $i setLocation $x $y
    if {$ot_oh_free} { $i setPlacementStatus PLACED } else { $i setPlacementStatus FIRM; lappend ot_oh_firm $nm }
    incr k
  }
  incr ot_oh_n
}
if {$ot_oh_n > 0} {
  set_dont_touch [get_cells ot_outhold_*]
  foreach n $ot_oh_dt { $n setDoNotTouch 1 }
}
if {[info exists ::env(RESULTS_DIR)]} {
  set fh [open $::env(RESULTS_DIR)/ot_inhold_firm.txt a]; if {[llength $ot_oh_firm]} { puts $fh [join $ot_oh_firm "\n"] }; close $fh
}
puts "OUTHOLD: $ot_oh_n output hold stages (BUF + [$ot_oh_hb getName] + BUF [expr {$ot_oh_free ? {PLACED (free) seeded} : {FIRM}}] at the pin, $ot_oh_ns with the strong pad by OT_HOLD_PAD_STRONG_RE, hold cell dont_touch), $ot_oh_skip outputs skipped (not flop-driven)"
