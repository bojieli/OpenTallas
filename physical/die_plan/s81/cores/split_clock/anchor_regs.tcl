# S81-CORES3/SW 10-25 broadcast-register anchor (PRE_GLOBAL_PLACE, after face_flops.tcl / macro_if_flops.tcl).
# GEOM-REVIEW 04:35/05:47 vn_b: "pre_c next to u_g".  pre_c (128 coefficient flops, second stage after the pin
# registers pre_in) broadcasts to every lane of u_g; GPL pulled it to the W pin face (t42 centroid 31.6,146.0 vs u_g
# centroid 171.3,86.7), so the pre_c -> u_g broadcast crossed the whole core in one cycle.  This hook places the
# registers matching OT_ANCHOR_PAT FIRM as one compact block centred on OT_ANCHOR_XY (default: core centre = where the
# u_g mass sits), so the pre_in -> pre_c hop is the single-fanout reg -> reg wire and the broadcast starts in the middle
# of its consumers.  Names are appended to ot_face_flops.txt so face_flops_release.tcl frees them for DPL.
# Env: OT_ANCHOR_PAT (glob on instance names, required), OT_ANCHOR_XY ("x y" um, default core centre),
#      OT_ANCHOR_COLS (flops per row, default 16)
uplevel #0 {
set an_blk [ord::get_db_block]
set an_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set an_core [$an_blk getCoreArea]
set an_rows [$an_blk getRows]
set an_site [[lindex $an_rows 0] getSite]
set an_sw [$an_site getWidth]; set an_rh [$an_site getHeight]
set an_orient {}
foreach r $an_rows { dict set an_orient [lindex [$r getOrigin] 1] [$r getOrient] }
set an_pat $::env(OT_ANCHOR_PAT)
if {[info exists ::env(OT_ANCHOR_XY)] && $::env(OT_ANCHOR_XY) ne ""} {
  lassign $::env(OT_ANCHOR_XY) an_cx an_cy; set an_cx [expr {round($an_cx * $an_dbu)}]; set an_cy [expr {round($an_cy * $an_dbu)}]
} else { set an_cx [expr {([$an_core xMin] + [$an_core xMax]) / 2}]; set an_cy [expr {([$an_core yMin] + [$an_core yMax]) / 2}] }
set an_cols [expr {[info exists ::env(OT_ANCHOR_COLS)] ? $::env(OT_ANCHOR_COLS) : 16}]
set an_regs {}
foreach i [$an_blk getInsts] {
  if {[string match $an_pat [string map {\\ {}} [$i getName]]] && [[$i getMaster] isSequential] && [$i getPlacementStatus] ne "FIRM"} { lappend an_regs $i }
}
set an_regs [lsort -dictionary -command {apply {{a b} {string compare -nocase [$a getName] [$b getName]}}} $an_regs]
set an_n [llength $an_regs]
set an_blocked {}
foreach i [$an_blk getInsts] {
  if {[$i getPlacementStatus] ne "FIRM" && [[$i getMaster] getType] ne "BLOCK"} continue
  lappend an_blocked [$i getBBox]
}
proc an_free {x y w} {
  global an_blocked an_rh
  foreach b $an_blocked { if {$x + $w > [$b xMin] && $x < [$b xMax] && $y + $an_rh > [$b yMin] && $y < [$b yMax]} { return 0 } }
  return 1
}
if {$an_n} {
  set w0 [[[lindex $an_regs 0] getMaster] getWidth]
  set pitch [expr {(($w0 + $an_sw - 1) / $an_sw + 2) * $an_sw}]
  set nrow [expr {($an_n + $an_cols - 1) / $an_cols}]
  set x0 [expr {[$an_core xMin] + (($an_cx - $an_cols * $pitch / 2 - [$an_core xMin]) / $an_sw) * $an_sw}]
  set y0 [expr {[$an_core yMin] + (($an_cy - $nrow * $an_rh / 2 - [$an_core yMin]) / $an_rh) * $an_rh}]
  set fh [open $::env(RESULTS_DIR)/ot_face_flops.txt a]
  set k 0; set an_miss 0; set slot 0
  foreach i $an_regs {
    set placed 0
    while {!$placed && $slot < 4 * $an_n} {
      set x [expr {$x0 + ($slot % $an_cols) * $pitch}]; set y [expr {$y0 + ($slot / $an_cols) * $an_rh}]
      incr slot
      if {[an_free $x $y [[$i getMaster] getWidth]]} { set placed 1 }
    }
    if {!$placed} { incr an_miss; continue }
    if {[dict exists $an_orient $y]} { $i setOrient [dict get $an_orient $y] }
    $i setLocation $x $y; $i setPlacementStatus FIRM
    puts $fh "[$i getName]\tANCHOR\t[expr {$x / double($an_dbu)}]\t[expr {$y / double($an_dbu)}]\t$an_pat"
    incr k
  }
  close $fh
  puts "OT_ANCHOR $an_pat: $k of $an_n registers FIRM in a [format %.1f [expr {$an_cols * $pitch / double($an_dbu)}]] x [format %.1f [expr {$nrow * $an_rh / double($an_dbu)}]] um block at ([format %.1f [expr {$an_cx / double($an_dbu)}]],[format %.1f [expr {$an_cy / double($an_dbu)}]]); $an_miss without a slot"
} else { error "OT_ANCHOR: no register matches '$an_pat'" }
}
