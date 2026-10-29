# HBM-CORES-KITS-18 2026-10-29 (GEOM-58/59 rst_n far-pin class): anchor the reset entry stage at the rst_n pin.
# Sourced by face_flops.tcl (PRE_GLOBAL_PLACE hook, global scope, after the face-flop pass) as /work/reset_tree.tcl.
# Uses face_flops' own face-band slot grid (ff_occ / ff_cpitch / ff_rows), so an anchored flop never shares a slot with a
# face flop.  ra_release 1 = append to ot_face_flops.txt (face_flops_release.tcl -> PLACED before DPL, like face flops);
# ra_release 0 = stays FIRM through DPL.  No buffer, no ECO, no new check: placement constraint only.
# Settings (written by the kit variant): ra_pin, ra_re (regexp on instance names), ra_release
set ra_bt [$ff_blk findBTerm $ra_pin]
if {$ra_bt eq "NULL" || $ra_bt eq ""} { error "OT_RESET_ANCHOR no port $ra_pin" }
set ra_bb [[lindex [$ra_bt getBPins] 0] getBBox]
set ra_px [expr {([$ra_bb xMin] + [$ra_bb xMax]) / 2}]; set ra_py [expr {([$ra_bb yMin] + [$ra_bb yMax]) / 2}]
set ra_d [list [list [expr {$ra_px - $ff_x0}] W] [list [expr {$ff_x1 - $ra_px}] E] [list [expr {$ra_py - $ff_y0}] S] [list [expr {$ff_y1 - $ra_py}] N]]
set ra_face [lindex [lsort -integer -index 0 $ra_d] 0 1]
set ra_list {}
foreach i [$ff_blk getInsts] { if {[regexp $ra_re [$i getName]] && [ff_is_ff $i]} { lappend ra_list [list [$i getName] $i] } }
set ra_list [lsort -index 0 $ra_list]
if {[llength $ra_list] == 0} { error "OT_RESET_ANCHOR no flop matches $ra_re" }
set ra_n 0
set ra_fh [open $::env(RESULTS_DIR)/ot_face_flops.txt a]
foreach e $ra_list {
  set f [lindex $e 1]
  set w [[$f getMaster] getWidth]
  set placed 0
  if {$ra_face in {E W}} {
    set row [expr {max(0, min(([llength $ff_rows] - 1), ($ra_py - $ff_y0) / $ff_rh))}]
    for {set c 0} {$c < 400 && !$placed} {incr c} {
      foreach dr {0 1 -1 2 -2} {
        set r [expr {$row + $dr}]
        if {$r < 0 || $r >= [llength $ff_rows] || [dict exists $ff_occ "$ra_face,$r,$c"]} continue
        dict set ff_occ "$ra_face,$r,$c" 1
        set cy [expr {$ff_y0 + $r * $ff_rh}]
        set cx [expr {$ra_face eq "W" ? $ff_x0 + $c * $ff_cpitch : $ff_x1 - $c * $ff_cpitch - $w}]
        set placed 1; break
      }
    }
  } else {
    set col [expr {($ra_px - $ff_x0) / $ff_cpitch}]
    for {set r 0} {$r < 400 && !$placed} {incr r} {
      foreach dc {0 -1 1 -2 2} {
        set c [expr {$col + $dc}]
        if {$c < 0 || [dict exists $ff_occ "$ra_face,$r,$c"]} continue
        dict set ff_occ "$ra_face,$r,$c" 1
        set cx [expr {min($ff_x0 + $c * $ff_cpitch, $ff_x1 - $w)}]
        set cy [expr {$ra_face eq "S" ? $ff_y0 + $r * $ff_rh : $ff_y1 - ($r + 1) * $ff_rh}]
        set placed 1; break
      }
    }
  }
  if {!$placed} { error "OT_RESET_ANCHOR no slot for [lindex $e 0]" }
  set cx [expr {$ff_x0 + (($cx - $ff_x0) / $ff_sw) * $ff_sw}]
  if {[$f getPlacementStatus] eq "FIRM"} { $f setPlacementStatus PLACED }
  if {[dict exists $ff_orient $cy]} { $f setOrient [dict get $ff_orient $cy] }
  $f setLocation $cx $cy
  $f setPlacementStatus FIRM
  if {$ra_release} { puts $ra_fh "[$f getName]\t$ra_face\t[expr {$cx / double($ff_dbu)}]\t[expr {$cy / double($ff_dbu)}]\t$ra_pin" }
  puts "OT_RESET_ANCHOR [lindex $e 0] $ra_face ([expr {$cx / double($ff_dbu)}], [expr {$cy / double($ff_dbu)}]) pin ([expr {$ra_px / double($ff_dbu)}], [expr {$ra_py / double($ff_dbu)}]) release $ra_release"
  incr ra_n
}
close $ra_fh
puts "OT_RESET_ANCHOR anchored $ra_n flops at $ra_pin ($ra_face face), release $ra_release"
