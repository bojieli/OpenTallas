# S81 scoped forwarding-only HB bypass; original own-output/status stages retained.
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
if {[info exists ::env(OT_IOHOLD_IN)] && $::env(OT_IOHOLD_IN)} {
  source /probe/leaf_inhold.tcl
}
set ot_oh_blk [ord::get_db_block]
set ot_oh_hb [[ord::get_db] findMaster [expr {[info exists ::env(OT_INHOLD_MASTER)] ? $::env(OT_INHOLD_MASTER) : "HB4xp67_ASAP7_75t_R"}]]
set ot_oh_bf [[ord::get_db] findMaster [expr {([info exists ::env(OT_INHOLD_DRV)] && $::env(OT_INHOLD_DRV) ne "") ? $::env(OT_INHOLD_DRV) : "BUFx4f_ASAP7_75t_R"}]]
if {$ot_oh_hb eq "NULL" || $ot_oh_bf eq "NULL"} { error "OUTHOLD: master missing" }
set ot_oh_ca [$ot_oh_blk getCoreArea]
set ot_oh_bypass 0
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
  set pn [odb::dbNet_create $ot_oh_blk [format "ot_outhold_p%05d" $ot_oh_n]]
  $bt disconnect
  $bt connect $pn
  set forwarding 0
  if {[regexp {^lo\[([0-9]+)\]$} [$bt getName] -> bit] && $bit<828} {set forwarding 1}
  if {[regexp {^co\[([0-9]+)\]$} [$bt getName] -> bit] && $bit>=212} {set forwarding 1}
  set stages [list $ot_oh_bf $ot_oh_hb $ot_oh_bf]
  if {$forwarding} {set stages [list $ot_oh_bf $ot_oh_bf];incr ot_oh_bypass}
  set cur $net; set k 0
  foreach m $stages {
    set hold [expr {$m eq $ot_oh_hb}]
    set nm [format "%s_%05d_%d" [expr {$hold ? "ot_outhold" : "ot_ohdrv"}] $ot_oh_n $k]
    set i [odb::dbInst_create $ot_oh_blk $m $nm]
    [$i findITerm A] connect $cur
    if {$k == [llength $stages]-1} {
      [$i findITerm Y] connect $pn
    } else {
      set n2 [odb::dbNet_create $ot_oh_blk [format "ot_outhold_n%05d_%d" $ot_oh_n $k]]
      [$i findITerm Y] connect $n2
      set cur $n2
    }
    if {$hold} { lappend ot_oh_dt [[$i findITerm A] getNet] }
    $i setOrient R0; $i setLocation $x $y; $i setPlacementStatus FIRM
    lappend ot_oh_firm $nm
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
puts "OUTHOLD: $ot_oh_n output hold stages (BUF + [$ot_oh_hb getName] + BUF FIRM at the pin, hold cell dont_touch), $ot_oh_skip outputs skipped (not flop-driven)"

puts "S81_FORWARD_HB outputs: $ot_oh_bypass forwarding HB bypasses; both strong BUF stages retained; own-output/status HB unchanged"
