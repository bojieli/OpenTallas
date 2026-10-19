# PRE_GLOBAL_PLACE hook (HKV-HROOTK1 2026-10-19): FEED-THROUGH relay flops at the midpoint of their two pins.
# A feed-through relay flop is a register whose D comes from ONE input port and whose Q drives ONE output port, each
# through at most OT_FTMID_HOPS single-fanout INV / BUF / HB cells (the pin hold stages included).  io_flop_at_pins.tcl
# anchors such a flop at the FIRST of its two pins it meets, so the whole pin-to-pin distance lands on one boundary
# budget: qkd_kvs_hroot_k1-k1-1cd36932b u_rly.r[103] FIRM at its i_r pin (71, 12) drove o_emb[103] at (248, 300),
# ~465 um of wire on the reg -> out side -> TT -36.2 (9 o_emb endpoints) while the in -> reg side carried ~2 um.
# The relay is a die relay stage (pin_regs disabled: the die calendar prices it), so its place is the middle of its
# span: each boundary then carries half the wire inside its own 0.2 T budget.  Placement only, 0 cycles, no SDC change.
#   OT_FTMID_MIN_UM (default 150): only flops whose pin-to-pin Manhattan span exceeds this move (short spans stay at
#     their pin, as io_flop_at_pins places them).
#   OT_FTMID_FRAC (default 0.5): position along the span measured from the input pin.
#   OT_FTMID_PORT_RE (optional): only output ports matching this regexp.
# Must be sourced BEFORE io_flop_at_pins.tcl (spec "pin_hook_before_flops"): a FIRM flop is kept there (ot_kept) and its
# second pin is skipped (ot_seen).  ft_flop_mid_release.tcl (spec "pre_dpl_extra") returns them to PLACED for DPL.
set ot_ft_blk [ord::get_db_block]
set ot_ft_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ot_ft_core [$ot_ft_blk getCoreArea]
set ot_ft_hops [expr {[info exists ::env(OT_FTMID_HOPS)] && $::env(OT_FTMID_HOPS) ne "" ? $::env(OT_FTMID_HOPS) : 8}]
set ot_ft_min [expr {[info exists ::env(OT_FTMID_MIN_UM)] && $::env(OT_FTMID_MIN_UM) ne "" ? $::env(OT_FTMID_MIN_UM) : 150.0}]
set ot_ft_frac [expr {[info exists ::env(OT_FTMID_FRAC)] && $::env(OT_FTMID_FRAC) ne "" ? $::env(OT_FTMID_FRAC) : 0.5}]
set ot_ft_re [expr {[info exists ::env(OT_FTMID_PORT_RE)] ? $::env(OT_FTMID_PORT_RE) : {}}]
proc ot_ft_isff {inst} { set m [[$inst getMaster] getName]; expr {[string match "DFF*" $m] || [string match "ASYNC_DFF*" $m]} }
proc ot_ft_isbuf {inst} { set m [[$inst getMaster] getName]; expr {[string match "INV*" $m] || [string match "BUF*" $m] || [string match "HB*" $m]} }
proc ot_ft_drv {net} { foreach it [$net getITerms] { if {[$it isOutputSignal]} { return $it } }; return "" }
# sinks of a net: input ITerms plus OUTPUT ports (an INPUT port is the net's driver)
proc ot_ft_nsinks {net} {
  set n 0
  foreach bt [$net getBTerms] { if {[$bt getIoType] eq "OUTPUT"} { incr n } }
  foreach it [$net getITerms] { if {[$it isInputSignal]} { incr n } }
  return $n
}
proc ot_ft_pin_xy {bt dbu} {
  set bb [$bt getBBox]
  return [list [expr {double([$bb xMin] + [$bb xMax]) / 2.0 / $dbu}] [expr {double([$bb yMin] + [$bb yMax]) / 2.0 / $dbu}]]
}
# output port -> its launching flop, through single-fanout buffer cells
proc ot_ft_launch {bt hops} {
  set net [$bt getNet]; if {$net eq "NULL"} { return "" }
  for {set h 0} {$h < $hops} {incr h} {
    if {[ot_ft_nsinks $net] != 1} { return "" }
    set d [ot_ft_drv $net]; if {$d eq ""} { return "" }
    set inst [$d getInst]
    if {[ot_ft_isff $inst]} { return $inst }
    if {![ot_ft_isbuf $inst]} { return "" }
    set net ""
    foreach it [$inst getITerms] { if {[$it isInputSignal] && [$it getNet] ne "NULL"} { set net [$it getNet] } }
    if {$net eq ""} { return "" }
  }
  return ""
}
# flop D -> the input port feeding it, through single-fanout buffer cells
proc ot_ft_source {ff hops} {
  set net ""
  foreach it [$ff getITerms] { if {[[$it getMTerm] getName] eq "D"} { set net [$it getNet] } }
  if {$net eq "" || $net eq "NULL"} { return "" }
  for {set h 0} {$h < $hops} {incr h} {
    if {[ot_ft_nsinks $net] != 1} { return "" }
    foreach bt [$net getBTerms] { if {[$bt getIoType] eq "INPUT"} { return $bt } }
    set d [ot_ft_drv $net]; if {$d eq ""} { return "" }
    set inst [$d getInst]
    if {![ot_ft_isbuf $inst]} { return "" }
    set net ""
    foreach it [$inst getITerms] { if {[$it isInputSignal] && [$it getNet] ne "NULL"} { set net [$it getNet] } }
    if {$net eq ""} { return "" }
  }
  return ""
}
set cx0 [expr {double([$ot_ft_core xMin]) / $ot_ft_dbu}]; set cx1 [expr {double([$ot_ft_core xMax]) / $ot_ft_dbu}]
set cy0 [expr {double([$ot_ft_core yMin]) / $ot_ft_dbu}]; set cy1 [expr {double([$ot_ft_core yMax]) / $ot_ft_dbu}]
set ot_ft_list {}; set ot_ft_short 0; set ot_ft_span 0.0; set ot_ft_seen [dict create]
foreach bt [$ot_ft_blk getBTerms] {
  if {[$bt getIoType] ne "OUTPUT"} continue
  if {$ot_ft_re ne "" && ![regexp -- $ot_ft_re [$bt getName]]} continue
  set ff [ot_ft_launch $bt $ot_ft_hops]; if {$ff eq ""} continue
  # the flop's Q must reach only this port (a flop with internal loads is not a pure relay)
  set qn 0
  foreach it [$ff getITerms] { if {[$it isOutputSignal] && [$it getNet] ne "NULL"} { incr qn [ot_ft_nsinks [$it getNet]] } }
  if {$qn != 1} continue
  if {[$ff isFixed] || [dict exists $ot_ft_seen [$ff getName]]} continue
  set ib [ot_ft_source $ff $ot_ft_hops]; if {$ib eq ""} continue
  lassign [ot_ft_pin_xy $ib $ot_ft_dbu] ix iy
  lassign [ot_ft_pin_xy $bt $ot_ft_dbu] ox oy
  set span [expr {abs($ox - $ix) + abs($oy - $iy)}]
  if {$span <= $ot_ft_min} { incr ot_ft_short; continue }
  set w [expr {double([[$ff getMaster] getWidth]) / $ot_ft_dbu}]
  set h [expr {double([[$ff getMaster] getHeight]) / $ot_ft_dbu}]
  set x [expr {min(max($ix + $ot_ft_frac * ($ox - $ix) - $w / 2.0, $cx0), $cx1 - $w)}]
  set y [expr {min(max($iy + $ot_ft_frac * ($oy - $iy) - $h / 2.0, $cy0), $cy1 - $h)}]
  # snap to the row grid (rows start at cy0, one row per cell height) so the anchor packer sees row-aligned sites
  set y [expr {$cy0 + round(($y - $cy0) / $h) * $h}]
  $ff setLocation [expr {round($x * $ot_ft_dbu)}] [expr {round($y * $ot_ft_dbu)}]
  $ff setPlacementStatus FIRM
  dict set ot_ft_seen [$ff getName] 1
  lappend ot_ft_list [$ff getName]
  set ot_ft_span [expr {max($ot_ft_span, $span)}]
}
if {[llength $ot_ft_list]} {
  set ot_anchor_script /src/physical/common_flow/anchor_row_packing.tcl
  if {![file exists $ot_anchor_script] && [info script] ne ""} {
    set ot_anchor_script [file join [file dirname [info script]] anchor_row_packing.tcl]
  }
  source $ot_anchor_script
  ot_anchor_pack::repair $ot_ft_blk $ot_ft_list
}
set fh [open $::env(RESULTS_DIR)/ot_ft_flop_mid.txt w]
foreach n $ot_ft_list { puts $fh $n }
close $fh
puts [format "OT_FTMID placed %d feed-through relay flops at %.2f of their pin span (longest %.1f um; %d spans <= %.0f um left to io_flop_at_pins)" \
        [llength $ot_ft_list] $ot_ft_frac $ot_ft_span $ot_ft_short $ot_ft_min]
