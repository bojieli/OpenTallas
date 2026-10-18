# Regional clock root (LOCAL_SPLIT box form, Q-D2DCLK 2026-10-18; x-cluster form = clock_split_x.tcl).
# Move the std-cell clock sinks placed inside each box of OT_CKR_BOXES ("x0,y0,x1,y1;..." um) off the clock port net onto
# one BUFx24 regional root at the group's centroid, so CTS builds a short local tree for that group instead of hanging it
# on one late trunk branch.  CTS latency balancing matches the regional root to the main root's insertion.  Same port,
# clock, flops, constraints; macros stay on the main tree.  OT_CKR_PORT = clock port (default clk); OT_CKR_MIN = minimum
# sinks a box must hold (default 16) or the hook errors.
set ot_ckr_blk [ord::get_db_block]
if {[$ot_ckr_blk findInst ot_ckregion_0] eq "NULL"} {
  if {![info exists ::env(OT_CKR_BOXES)] || $::env(OT_CKR_BOXES) eq ""} { error "CLOCK_REGION: OT_CKR_BOXES unset" }
  set ot_ckr_port [expr {[info exists ::env(OT_CKR_PORT)] && $::env(OT_CKR_PORT) ne "" ? $::env(OT_CKR_PORT) : "clk"}]
  set ot_ckr_min [expr {[info exists ::env(OT_CKR_MIN)] && $::env(OT_CKR_MIN) ne "" ? $::env(OT_CKR_MIN) : 16}]
  set ot_ckr_u [[ord::get_db_tech] getDbUnitsPerMicron]
  set ot_ckr_bt [$ot_ckr_blk findBTerm $ot_ckr_port]
  if {$ot_ckr_bt eq "NULL"} { error "CLOCK_REGION: no $ot_ckr_port port" }
  set ot_ckr_net [$ot_ckr_bt getNet]
  set ot_ckr_m [[ord::get_db] findMaster BUFx24_ASAP7_75t_R]
  set k 0
  foreach box [split $::env(OT_CKR_BOXES) ";"] {
    lassign [split [string trim $box] ","] x0 y0 x1 y1
    set grp {}
    foreach it [$ot_ckr_net getITerms] {
      if {![$it isInputSignal]} continue
      set inst [$it getInst]
      if {[[$inst getMaster] isBlock]} continue
      set bb [$inst getBBox]
      set cx [expr {([$bb xMin] + [$bb xMax]) / 2.0 / $ot_ckr_u}]; set cy [expr {([$bb yMin] + [$bb yMax]) / 2.0 / $ot_ckr_u}]
      if {$cx >= $x0 && $cx <= $x1 && $cy >= $y0 && $cy <= $y1} { lappend grp [list $cx $cy $it] }
    }
    set n [llength $grp]
    if {$n < $ot_ckr_min} { error "CLOCK_REGION: box {$box} holds only $n sinks (< $ot_ckr_min)" }
    set sx 0.0; set sy 0.0
    foreach e $grp { set sx [expr {$sx + [lindex $e 0]}]; set sy [expr {$sy + [lindex $e 1]}] }
    set b [odb::dbInst_create $ot_ckr_blk $ot_ckr_m ot_ckregion_$k]
    $b setLocation [expr {int($sx / $n * $ot_ckr_u)}] [expr {int($sy / $n * $ot_ckr_u)}]; $b setPlacementStatus PLACED
    set net [odb::dbNet_create $ot_ckr_blk ot_ckregion_${k}_clk]; $net setSigType CLOCK
    [$b findITerm A] connect $ot_ckr_net; [$b findITerm Y] connect $net
    foreach e $grp { set it [lindex $e 2]; $it disconnect; $it connect $net }
    puts [format "CLOCK_REGION: root %d box {%s} %d sinks, BUFx24 at (%.1f, %.1f)" $k $box $n [expr {$sx/$n}] [expr {$sy/$n}]]
    incr k
  }
  detailed_placement
}
