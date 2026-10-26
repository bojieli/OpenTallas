# PRE_GLOBAL_PLACE hook (STW-S81c-COLLA2 10-22, S81 HEAD ctl glue R7): place every kept relay stage of a planned chain at
# its planned station, FIRM through global placement (released before DPL by relay_chain_release.tcl).
# Why: a wirelength-driven global placement is indifferent to where the stages of a collinear register chain sit (same
# HPWL for any spacing) and collapsed the glue's 380-um-sized relay chains (r5m: stage 1 at the face, 2..n at the centre,
# 4,061 one-level paths over 1.1-2.0 mm, WNS -1,045 ps at 770 ps).
# Input: $::env(OT_RELAY_PLACE) lines "<inst> <x_um> <y_um> <chain>" (tools/s81_head/glue_relay_place.py); every cell
# below that hierarchy prefix (the kept ot_s81hd_rs32/rs8/kf/rv1/rr1 instance) is placed in a compact cluster at the
# station (clusters at one station stack upward), pushed outside any macro halo; cells on a port net are left to the pin
# hooks.  The placed names are written to $RESULTS_DIR/ot_relay_chain_place.txt.
set ot_rc_blk [ord::get_db_block]
set ot_rc_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ot_rc_plan {}
set fh [open $::env(OT_RELAY_PLACE) r]
foreach ln [split [read $fh] "\n"] {
  if {$ln eq "" || [string index $ln 0] eq "#"} continue
  dict set ot_rc_plan [lindex $ln 0] [list [lindex $ln 1] [lindex $ln 2]]
}
close $fh
set ot_rc_rows [$ot_rc_blk getRows]
set ot_rc_r0 [lindex $ot_rc_rows 0]
set ot_rc_site [$ot_rc_r0 getSite]
set ot_rc_sw [$ot_rc_site getWidth]
set ot_rc_rh [$ot_rc_site getHeight]
set ot_rc_core [$ot_rc_blk getCoreArea]
set ot_rc_x0 [$ot_rc_core xMin]; set ot_rc_y0 [$ot_rc_core yMin]; set ot_rc_x1 [$ot_rc_core xMax]; set ot_rc_y1 [$ot_rc_core yMax]
set ot_rc_orient {}
foreach r $ot_rc_rows { dict set ot_rc_orient [lindex [$r getOrigin] 1] [$r getOrient] }
# macro keep-outs (halo 10.8 um + 2 um)
set ot_rc_mac {}
set ot_rc_h [expr {int(12.8 * $ot_rc_dbu)}]
foreach i [$ot_rc_blk getInsts] {
  if {[[$i getMaster] isBlock]} {
    set b [$i getBBox]
    lappend ot_rc_mac [list [expr {[$b xMin]-$ot_rc_h}] [expr {[$b yMin]-$ot_rc_h}] [expr {[$b xMax]+$ot_rc_h}] [expr {[$b yMax]+$ot_rc_h}]]
  }
}
# group cells by planned prefix (clock / reset ports are global nets, not pin stations)
set ot_rc_glob_ports [expr {[info exists ::env(OT_RELAY_GLOBAL_PORTS)] ? $::env(OT_RELAY_GLOBAL_PORTS) : {ck rst_n seq_rst}}]
set ot_rc_cells {}
set ot_rc_skip 0
foreach i [$ot_rc_blk getInsts] {
  if {[[$i getMaster] isBlock]} continue
  set n [string map {\\ {}} [$i getName]]
  if {![regexp {^u_ot_pr_core[./](u_[A-Za-z0-9_]+)/} $n -> pfx]} continue
  if {![dict exists $ot_rc_plan $pfx]} continue
  if {[$i getPlacementStatus] in {FIRM LOCKED COVER}} continue
  set port 0
  foreach it [$i getITerms] {
    set nt [$it getNet]
    if {$nt eq "NULL" || $nt eq "" || [$nt getSigType] in {CLOCK POWER GROUND}} continue
    foreach bt [$nt getBTerms] { if {[$bt getName] ni $ot_rc_glob_ports} { set port 1 } }
    if {$port} break
  }
  if {$port} { incr ot_rc_skip; continue }
  dict lappend ot_rc_cells $pfx $i
}
set ot_rc_stack {}
set ot_rc_out [open $::env(RESULTS_DIR)/ot_relay_chain_place.txt w]
set ot_rc_n 0
foreach pfx [lsort [dict keys $ot_rc_cells]] {
  lassign [dict get $ot_rc_plan $pfx] xu yu
  set x [expr {int($xu * $ot_rc_dbu)}]; set y [expr {int($yu * $ot_rc_dbu)}]
  foreach m $ot_rc_mac {
    lassign $m mx0 my0 mx1 my1
    if {$x > $mx0 && $x < $mx1 && $y > $my0 && $y < $my1} {
      set d [list [list [expr {$x-$mx0}] $mx0 $y] [list [expr {$mx1-$x}] $mx1 $y] [list [expr {$y-$my0}] $x $my0] [list [expr {$my1-$y}] $x $my1]]
      lassign [lindex [lsort -integer -index 0 $d] 0] - x y
    }
  }
  # station key: 40 um grid; stack clusters upward
  set key "[expr {$x / (40*$ot_rc_dbu)}],[expr {$y / (40*$ot_rc_dbu)}]"
  set off [expr {[dict exists $ot_rc_stack $key] ? [dict get $ot_rc_stack $key] : 0}]
  set cells [dict get $ot_rc_cells $pfx]
  set nc [llength $cells]
  set ncol [expr {max(1, int(ceil(sqrt($nc * 4.0))))}]
  set pitch [expr {$ot_rc_sw * 20}]
  set k 0
  foreach c $cells {
    set cx [expr {$x + ($k % $ncol) * $pitch - ($ncol * $pitch) / 2}]
    set cy [expr {$y + ($off + $k / $ncol) * $ot_rc_rh}]
    set cx [expr {$ot_rc_x0 + (($cx - $ot_rc_x0) / $ot_rc_sw) * $ot_rc_sw}]
    set cy [expr {$ot_rc_y0 + (($cy - $ot_rc_y0) / $ot_rc_rh) * $ot_rc_rh}]
    set cx [expr {min(max($cx, $ot_rc_x0), $ot_rc_x1 - [[$c getMaster] getWidth])}]
    set cy [expr {min(max($cy, $ot_rc_y0), $ot_rc_y1 - $ot_rc_rh)}]
    $c setLocation $cx $cy
    if {[dict exists $ot_rc_orient $cy]} { $c setOrient [dict get $ot_rc_orient $cy] }
    $c setPlacementStatus FIRM
    puts $ot_rc_out [$c getName]
    incr k; incr ot_rc_n
  }
  dict set ot_rc_stack $key [expr {$off + int(ceil(double($nc) / $ncol)) + 1}]
}
close $ot_rc_out
puts "OT_RELAY_PLACE placed $ot_rc_n relay cells of [dict size $ot_rc_cells] planned instances FIRM at their stations ($ot_rc_skip port-net cells left to the pin hooks)"
