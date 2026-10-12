# PRE_GLOBAL_PLACE hook (safe-hbm 2026-10-08, reviewer decision R-b): put every IO pin register AT its die pin.
# ot_hcoll_port2 tall (1e2cc4ed6-tc) failed post-CTS TT -505 on IO pin -> flop wire: the RTL registers every port
# (pin flop, no logic between pin and flop), but timing-driven GPL pulled the pin flops into the logic.  Same technique
# as qwen_die_masters/rom_cap_at_pins.tcl: for every signal port whose net connects ONLY the port and ONE flop pin
# (input -> DFF D, or DFF Q -> output), the flop is placed FIRM just inside the core on the pin's edge, stacked
# OT_IOF_ROWS deep (rows for horizontal edges, columns for vertical ones) so neighbouring pins' flops do not pile up.
# io_flop_release.tcl (PRE_DETAIL_PLACE) returns them to PLACED so DPL legalises them.  Placement only: netlist unchanged,
# 0 cycles.
set ot_blk [ord::get_db_block]
set ot_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ot_core [$ot_blk getCoreArea]
set ot_x0 [expr {double([$ot_core xMin]) / $ot_dbu}]; set ot_x1 [expr {double([$ot_core xMax]) / $ot_dbu}]
set ot_y0 [expr {double([$ot_core yMin]) / $ot_dbu}]; set ot_y1 [expr {double([$ot_core yMax]) / $ot_dbu}]
set ot_rows [expr {[info exists ::env(OT_IOF_ROWS)] ? $::env(OT_IOF_ROWS) : 8}]
set ot_in [expr {[info exists ::env(OT_IOF_INSET)] ? $::env(OT_IOF_INSET) : 1.0}]
set ot_rh 0.27
set ot_list {}
array set ot_k {B 0 T 0 L 0 R 0}
foreach ot_bt [$ot_blk getBTerms] {
  set ot_net [$ot_bt getNet]
  if {$ot_net eq "NULL" || $ot_net eq ""} continue
  if {[$ot_net getSigType] ne "SIGNAL"} continue
  set ot_its [$ot_net getITerms]
  if {[llength $ot_its] != 1 || [llength [$ot_net getBTerms]] != 1} continue
  set ot_it [lindex $ot_its 0]
  set ot_ff [$ot_it getInst]
  set ot_pn [[$ot_it getMTerm] getName]
  set ot_dir [$ot_bt getIoType]
  set ot_mv {}
  # an output pin flop is mapped as DFF QN -> INV -> port (or Q -> BUF): follow one inverter / buffer stage
  if {$ot_dir eq "OUTPUT" && [regexp {^(INV|BUF)} [[$ot_ff getMaster] getName]]} {
    set ot_a ""
    foreach t [$ot_ff getITerms] { if {[$t isInputSignal]} { set ot_a $t } }
    if {$ot_a eq ""} continue
    set ot_n2 [$ot_a getNet]
    if {$ot_n2 eq "NULL" || $ot_n2 eq "" || [llength [$ot_n2 getITerms]] != 2} continue
    set ot_drv ""
    foreach t [$ot_n2 getITerms] { if {$t ne $ot_a} { set ot_drv $t } }
    lappend ot_mv $ot_ff
    set ot_ff [$ot_drv getInst]; set ot_pn [[$ot_drv getMTerm] getName]
  }
  if {![string match "DFF*" [[$ot_ff getMaster] getName]]} continue
  if {!(($ot_dir eq "INPUT" && $ot_pn eq "D") || ($ot_dir eq "OUTPUT" && ($ot_pn eq "Q" || $ot_pn eq "QN")))} continue
  if {[$ot_ff getPlacementStatus] in {FIRM LOCKED COVER}} continue
  set ot_bb [$ot_bt getBBox]
  set px [expr {([$ot_bb xMin] + [$ot_bb xMax]) / 2.0 / $ot_dbu}]
  set py [expr {([$ot_bb yMin] + [$ot_bb yMax]) / 2.0 / $ot_dbu}]
  set d [list [list B [expr {$py - $ot_y0}]] [list T [expr {$ot_y1 - $py}]] [list L [expr {$px - $ot_x0}]] [list R [expr {$ot_x1 - $px}]]]
  set side [lindex [lsort -real -index 1 $d] 0 0]
  set r [expr {$ot_k($side) % $ot_rows}]; incr ot_k($side)
  set w [expr {double([[$ot_ff getMaster] getWidth]) / $ot_dbu}]
  switch $side {
    B { set x [expr {$px - $w / 2}]; set y [expr {$ot_y0 + $ot_in + $r * $ot_rh}] }
    T { set x [expr {$px - $w / 2}]; set y [expr {$ot_y1 - $ot_in - ($r + 1) * $ot_rh}] }
    L { set x [expr {$ot_x0 + $ot_in + $r * ($w + 0.2)}]; set y $py }
    R { set x [expr {$ot_x1 - $ot_in - ($r + 1) * ($w + 0.2)}]; set y $py }
  }
  set x [expr {max($ot_x0, min($x, $ot_x1 - $w))}]
  set y [expr {max($ot_y0, min($y, $ot_y1 - $ot_rh))}]
  $ot_ff setLocation [expr {round($x * $ot_dbu)}] [expr {round($y * $ot_dbu)}]
  $ot_ff setPlacementStatus FIRM
  lappend ot_list [$ot_ff getName]
  foreach ot_b $ot_mv {
    # the output inverter / buffer sits beside its flop, toward the pin
    set bx [expr {$side eq "L" ? $x - double([[$ot_b getMaster] getWidth]) / $ot_dbu : ($side eq "R" ? $x + $w : $x + $w)}]
    set bx [expr {max($ot_x0, min($bx, $ot_x1 - double([[$ot_b getMaster] getWidth]) / $ot_dbu))}]
    $ot_b setLocation [expr {round($bx * $ot_dbu)}] [expr {round($y * $ot_dbu)}]
    $ot_b setPlacementStatus FIRM
    lappend ot_list [$ot_b getName]
  }
}
set ot_fh [open $::env(RESULTS_DIR)/ot_io_flop_at_pins.txt w]
puts $ot_fh [join $ot_list "\n"]
close $ot_fh
puts "OT_IOF fixed [llength $ot_list] IO pin flops at their pins (B $ot_k(B) T $ot_k(T) L $ot_k(L) R $ot_k(R))"
