# HBM-HARD-2-QOUT 11-07 (PRE_GLOBAL_PLACE): face flops first, then the pin_d stations FIRM at KIT/stage_pose.tsv with their QN
# inverter beside them.  Why: q2nf_stage_pose.py.  GPL-stranded inverters (vR1 u_bout q[167]: flop x 331, INV x 584) cost the
# TT misses.  Listed in ot_relay_mid.txt, so face_flops_release.tcl releases them before DPL.  No netlist change except the
# inverter master on long hops: FIRM cells do not get resized by repair_design, and an x1 inverter cannot drive a station hop.
source /work/face_flops.tcl
uplevel #0 {
set sp_blk [ord::get_db_block]
set sp_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set sp_rows [$sp_blk getRows]
set sp_row0 [lindex $sp_rows 0]
set sp_site [$sp_row0 getSite]
set sp_sw [$sp_site getWidth]; set sp_rh [$sp_site getHeight]
set sp_core [$sp_blk getCoreArea]; set sp_x0 [$sp_core xMin]; set sp_y0 [$sp_core yMin]
set sp_orient {}
foreach r $sp_rows { dict set sp_orient [lindex [$r getOrigin] 1] [$r getOrient] }
set sp_inv3 [[ord::get_db] findMaster INVx3_ASAP7_75t_R]
set sp_rel [open $::env(RESULTS_DIR)/ot_relay_mid.txt a]
set sp_n 0; set sp_miss 0; set sp_ninv 0; set sp_noinv 0; set sp_up 0
set sp_fh [open /work/stage_pose.tsv r]
foreach sp_ln [split [read $sp_fh] "\n"] {
  if {$sp_ln eq "" || [string index $sp_ln 0] eq "#"} continue
  lassign [split $sp_ln "\t"] sp_nm sp_x sp_y sp_hop
  set sp_db "[string map {[ \\[ ] \\]} $sp_nm]\$_DFF_P_"
  set sp_f [$sp_blk findInst $sp_db]
  if {$sp_f eq "NULL"} { incr sp_miss; continue }
  set sp_cx [expr {$sp_x0 + round(($sp_x * $sp_dbu - $sp_x0) / $sp_sw) * $sp_sw}]
  set sp_cy [expr {$sp_y0 + round(($sp_y * $sp_dbu - $sp_y0) / $sp_rh) * $sp_rh}]
  if {[dict exists $sp_orient $sp_cy]} { $sp_f setOrient [dict get $sp_orient $sp_cy] }
  $sp_f setLocation $sp_cx $sp_cy
  $sp_f setPlacementStatus FIRM
  puts $sp_rel [$sp_f getName]
  incr sp_n
  set sp_q [[$sp_f findITerm QN] getNet]
  set sp_inv {}
  foreach it [$sp_q getITerms] { if {[$it isInputSignal] && [string match "INV*" [[[$it getInst] getMaster] getName]]} { lappend sp_inv [$it getInst] } }
  if {[llength $sp_inv] != 1} { incr sp_noinv; continue }
  set sp_i [lindex $sp_inv 0]
  if {$sp_hop > 40.0 && $sp_inv3 ne "NULL"} { if {[$sp_i swapMaster $sp_inv3]} { incr sp_up } }
  set sp_ix [expr {$sp_cx + [[$sp_f getMaster] getWidth]}]
  if {[dict exists $sp_orient $sp_cy]} { $sp_i setOrient [dict get $sp_orient $sp_cy] }
  $sp_i setLocation $sp_ix $sp_cy
  $sp_i setPlacementStatus FIRM
  puts $sp_rel [$sp_i getName]
  incr sp_ninv
}
close $sp_fh; close $sp_rel
puts "OT_STAGE_POSE flops $sp_n missing $sp_miss inverters $sp_ninv (upsized $sp_up) without_one_inverter $sp_noinv"
if {$sp_miss} { error "OT_STAGE_POSE: $sp_miss stations not found in the netlist" }
}
