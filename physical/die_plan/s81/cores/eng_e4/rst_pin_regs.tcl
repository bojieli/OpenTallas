# PATH-S81/E4 PRE_GLOBAL_PLACE hook: RESET PIN REGISTERS at the reset pin.  The flops whose async reset (or D) is the
# raw reset port net (through <= 3 single-fanout BUF / INV) are the reset relay's pin landing (ot_s81eng_reset3n32
# root_d / root_r); face_flops.tcl skips reset ports, so GPL left them wherever their Q loads pulled them (E3: rst_n
# removal -287.9).  Anchored FIRM just inside the core edge facing the pin, legalised by anchor_row_packing.tcl and
# released to PLACED with the other anchors (rst_pin_regs_release.tcl).  Placement only: 0 cycles, no netlist change.
#   OT_RPR_PORTS (default rst_n)
set rpr_blk [ord::get_db_block]
set rpr_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set rpr_ports [expr {[info exists ::env(OT_RPR_PORTS)] ? $::env(OT_RPR_PORTS) : "rst_n"}]
set rpr_core [$rpr_blk getCoreArea]
set rpr_list {}
foreach pn $rpr_ports {
  set bt [$rpr_blk findBTerm $pn]
  if {$bt eq "NULL" || $bt eq ""} { error "rst_pin_regs: no port $pn" }
  set bb [$bt getBBox]
  set px [expr {([$bb xMin] + [$bb xMax]) / 2}]; set py [expr {([$bb yMin] + [$bb yMax]) / 2}]
  set todo [list [list [$bt getNet] 0]]; set ffs {}
  while {[llength $todo]} {
    lassign [lindex $todo 0] n d; set todo [lrange $todo 1 end]
    foreach it [$n getITerms] {
      if {![$it isInputSignal]} continue
      set i [$it getInst]; set m [[$i getMaster] getName]
      if {[[$i getMaster] isSequential]} { lappend ffs $i; continue }
      if {$d < 3 && [regexp {^(BUF|INV|HB)} $m]} {
        foreach o [$i getITerms] { if {[$o isOutputSignal] && [$o getNet] ne "NULL"} { lappend todo [list [$o getNet] [expr {$d + 1}]] } }
      }
    }
  }
  if {[llength $ffs] > 16} { error "rst_pin_regs: $pn reaches [llength $ffs] flops directly (want a registered relay root)" }
  # nearest core edge to the pin
  set cx0 [$rpr_core xMin]; set cx1 [$rpr_core xMax]; set cy0 [$rpr_core yMin]; set cy1 [$rpr_core yMax]
  set k 0
  foreach f $ffs {
    set w [[$f getMaster] getWidth]; set h [[$f getMaster] getHeight]
    set x [expr {min(max($px - $w / 2 + ($k - [llength $ffs] / 2) * $w, $cx0), $cx1 - $w)}]
    set y [expr {min(max($py, $cy0), $cy1 - $h)}]
    set y [expr {$cy0 + round(double($y - $cy0) / $h) * $h}]
    $f setLocation [expr {round($x)}] [expr {round($y)}]
    $f setPlacementStatus FIRM
    lappend rpr_list [$f getName]; incr k
  }
  puts "OT_RPR $pn: anchored [llength $ffs] reset pin registers at ([format %.2f [expr {$px / double($rpr_dbu)}]], [format %.2f [expr {$py / double($rpr_dbu)}]])"
}
if {[llength $rpr_list]} {
  set ot_anchor_script [file join [file dirname [info script]] anchor_row_packing.tcl]
  source $ot_anchor_script
  ot_anchor_pack::repair $rpr_blk $rpr_list
}
set fh [open $::env(RESULTS_DIR)/ot_rst_pin_regs.txt w]; foreach n $rpr_list { puts $fh $n }; close $fh
