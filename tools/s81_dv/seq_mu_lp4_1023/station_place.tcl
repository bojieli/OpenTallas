# pin_hook_after_flops (STW-S81c-COLLA4-SEQ 10-22, dsdv_seq_host_mu_lp rev3): place the kept single-flop relay stages of the
# parent's reset runs at planned stations, FIRM through global placement (released before DPL by station_release.tcl).
# Why: rev2 gate (ep5 20261022-161657): GPL is indifferent to where the stages of a collinear register chain sit, so the
# hslot run u_rh (2 sync + 7 tree stages, rst_l1 at the E face y~694 -> u_hs/rst_n at (241,43)) ended with one ~600 um
# hop (u_rh.rst_n -> u_hs/rst_n -175 ps), and the u_l0 run had to be rebuilt in the parent (see dsdv_seq_host_mu_lp.sv rev3).
# Plan file $::env(OT_STATION_PLAN): lines "<tcl regexp on the instance name, backslashes stripped> <x_um> <y_um>"; the
# first matching line wins; cells on a port net are never moved (the pin hooks own them).  Writes
# $RESULTS_DIR/ot_station_place.txt (the names placed) and prints OT_STATION_PLACE.
set ot_st_blk [ord::get_db_block]
set ot_st_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ot_st_plan {}
set fh [open $::env(OT_STATION_PLAN) r]
foreach ln [split [read $fh] "\n"] {
  if {$ln eq "" || [string index $ln 0] eq "#"} continue
  lappend ot_st_plan [list [lindex $ln 0] [lindex $ln 1] [lindex $ln 2]]
}
close $fh
set ot_st_r0 [lindex [$ot_st_blk getRows] 0]
set ot_st_sw [[$ot_st_r0 getSite] getWidth]
set ot_st_rh [[$ot_st_r0 getSite] getHeight]
set ot_st_core [$ot_st_blk getCoreArea]
set ot_st_x0 [$ot_st_core xMin]; set ot_st_y0 [$ot_st_core yMin]; set ot_st_x1 [$ot_st_core xMax]; set ot_st_y1 [$ot_st_core yMax]
set ot_st_orient {}
foreach r [$ot_st_blk getRows] { dict set ot_st_orient [lindex [$r getOrigin] 1] [$r getOrient] }
set ot_st_used {}
set ot_st_out [open $::env(RESULTS_DIR)/ot_station_place.txt w]
set ot_st_n 0; set ot_st_skip 0
foreach i [$ot_st_blk getInsts] {
  if {[[$i getMaster] isBlock]} continue
  if {[$i getPlacementStatus] in {FIRM LOCKED COVER}} continue
  set n [string map {\\ {}} [$i getName]]
  set hit ""
  foreach p $ot_st_plan { if {[regexp -- [lindex $p 0] $n]} { set hit $p; break } }
  if {$hit eq ""} continue
  set port 0
  foreach it [$i getITerms] {
    set nt [$it getNet]
    if {$nt eq "NULL" || $nt eq "" || [$nt getSigType] in {CLOCK POWER GROUND}} continue
    foreach bt [$nt getBTerms] { if {[$bt getName] ni {ck rst_n}} { set port 1 } }
    if {$port} break
  }
  if {$port} { incr ot_st_skip; continue }
  set key "[lindex $hit 1],[lindex $hit 2]"
  set k [expr {[dict exists $ot_st_used $key] ? [dict get $ot_st_used $key] : 0}]
  dict set ot_st_used $key [expr {$k + 1}]
  set x [expr {int([lindex $hit 1] * $ot_st_dbu) + ($k % 4) * 8 * $ot_st_sw}]
  set y [expr {int([lindex $hit 2] * $ot_st_dbu) + ($k / 4) * $ot_st_rh}]
  set x [expr {$ot_st_x0 + (($x - $ot_st_x0) / $ot_st_sw) * $ot_st_sw}]
  set y [expr {$ot_st_y0 + (($y - $ot_st_y0) / $ot_st_rh) * $ot_st_rh}]
  set x [expr {min(max($x, $ot_st_x0), $ot_st_x1 - [[$i getMaster] getWidth])}]
  set y [expr {min(max($y, $ot_st_y0), $ot_st_y1 - $ot_st_rh)}]
  $i setLocation $x $y
  if {[dict exists $ot_st_orient $y]} { $i setOrient [dict get $ot_st_orient $y] }
  $i setPlacementStatus FIRM
  puts $ot_st_out [$i getName]
  incr ot_st_n
}
close $ot_st_out
puts "OT_STATION_PLACE placed $ot_st_n cells FIRM at [dict size $ot_st_used] stations ($ot_st_skip port-net cells left to the pin hooks)"
