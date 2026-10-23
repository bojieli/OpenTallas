# PRE_GLOBAL_PLACE hook (STEWARD-HBMd/E86 2026-10-23, kit e86rt): face-anchor the up_in capture flops.
# up_in (344 b, S face) is the conveyor seam: its driver is the neighbour tile's up_out FLOP and it is captured, through the
# X slice select (AND-OR), by X[60..63] -- the tile's pin register for these pins (a separate register would add one edge to
# every conveyor hop).  Coordinator review 10-23 (f67e2e265): pin -> reg p90 142 um, 344 pins "w/o register" = these flops
# pulled into the array by GPL.  This hook places every flop reached from an up_in port through <= 2 combinational cells
# FIRM just inside the S core edge at its pin's x (staggered rows behind the io_flop_at_pins face columns); upin_release.tcl
# (PRE_DETAIL_PLACE) returns them to PLACED for DPL.  Placement only, 0 cycles.
set ua_blk [ord::get_db_block]
set ua_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ua_core [$ua_blk getCoreArea]
set ua_y0 [$ua_core yMin]; set ua_x0 [$ua_core xMin]; set ua_x1 [$ua_core xMax]
set ua_row [expr {round(0.27 * $ua_dbu)}]
# behind the 4 io_flop_at_pins columns (default gap 1 um + 4 rows) of the S-face output flops
set ua_gap [expr {[info exists ::env(OT_UPIN_GAP_UM)] ? $::env(OT_UPIN_GAP_UM) : 4.0}]
set ua_rows [expr {[info exists ::env(OT_UPIN_ROWS)] ? $::env(OT_UPIN_ROWS) : 6}]
proc ua_isff {inst} {
  foreach mt [[$inst getMaster] getMTerms] { if {[$mt getSigType] eq "CLOCK"} { return 1 } }
  return 0
}
set ua_list {}
set ua_n 0; set ua_ports 0
foreach bt [$ua_blk getBTerms] {
  if {![string match "up_in*" [$bt getName]]} continue
  incr ua_ports
  set net [$bt getNet]
  if {$net eq "NULL"} continue
  set bb [$bt getBBox]
  set px [expr {([$bb xMin] + [$bb xMax]) / 2}]
  set front [list $net]; set found {}
  for {set d 0} {$d < 3 && [llength $front] && ![llength $found]} {incr d} {
    set nxt {}
    foreach n $front {
      foreach it [$n getITerms] {
        if {![$it isInputSignal]} continue
        set i [$it getInst]
        if {[ua_isff $i]} { lappend found $i; continue }
        foreach ot [$i getITerms] { if {[$ot isOutputSignal] && [$ot getNet] ne "NULL"} { lappend nxt [$ot getNet] } }
      }
    }
    set front $nxt
  }
  foreach i $found {
    if {[$i getPlacementStatus] eq "FIRM" || [$i getPlacementStatus] eq "LOCKED"} continue
    set w [[$i getMaster] getWidth]
    set r [expr {$ua_n % $ua_rows}]
    set x [expr {max($ua_x0, min($ua_x1 - $w, $px - $w / 2))}]
    set x [expr {$x - ($x - $ua_x0) % round(0.054 * $ua_dbu)}]
    set y [expr {$ua_y0 + (int(ceil($ua_gap / 0.27)) + $r) * $ua_row}]
    $i setLocation $x $y
    $i setPlacementStatus FIRM
    lappend ua_list [$i getName]
    incr ua_n
  }
}
set fh [open $::env(RESULTS_DIR)/ot_upin_anchor.txt w]; puts $fh [join $ua_list "\n"]; close $fh
puts "UPIN_ANCHOR ports=$ua_ports flops=$ua_n (FIRM at the S face, rows=$ua_rows gap=${ua_gap}um)"
if {$ua_n == 0} { error "UPIN_ANCHOR: no up_in capture flop found" }
