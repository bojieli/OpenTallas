# FLOW-12 2026-10-30 (COORD 20:13 ruling (2), opt-in OT_PRD_FROM=route; shared form of the DIE-QC-50 P6/P8eco recipe,
# BTAB SIGNED TT +306.81 / FF +7.44, DRC 0, CLK_GEOM_DIFF PASS): route-keeping post-route ECO.
# prd_mk.sh seeds the ECO with the kit's ROUTED 5_2_route.odb (as 4_cts.odb), so after prd_hook.tcl's repair the block
# still carries the signed-off detailed wires.  ot_prd_route_keep rips the wires of exactly the nets the ECO touched,
# judged against that routed reference DB (read side by side, read-only):
#   - nets the reference does not have (ECO-created; normally wireless already),
#   - nets whose connectivity changed (instance/master-terminal + port list),
#   - nets on an instance that is new, moved / re-oriented (DPL legalisation) or re-mastered (sizing).
# Every other net keeps its routed metal; ORFS detail_route then routes only the ripped nets (incremental DRT on the
# guides of the ECO's incremental GRT).  A clock net (clk_freeze list) that would be ripped stops the ECO: the clock is
# frozen, and clk_freeze_check.sh compares clock WIRES (not --pre-unrouted) for route-keeping dirs.
# No check, margin or corner changes; OT_PRD_FROM=grt (default) never sources this file.
proc ot_prd_net_sig {n} {
  set l {}
  foreach t [$n getITerms] { lappend l "[[$t getInst] getName]/[[$t getMTerm] getName]" }
  foreach t [$n getBTerms] { lappend l "port:[$t getName]" }
  return [lsort $l]
}
proc ot_prd_inst_key {i} {
  return [list [[$i getMaster] getName] [$i getLocation] [$i getOrient]]
}
# -> dict {sig {net -> sig} inst {inst -> key} wired {net -> 1 if routed}} of a block
proc ot_prd_route_snapshot {b} {
  set sig [dict create]; set ik [dict create]; set wired [dict create]
  foreach n [$b getNets] {
    if {[$n getSigType] in {POWER GROUND}} continue
    dict set sig [$n getName] [ot_prd_net_sig $n]
    if {[$n getWire] ne "NULL"} { dict set wired [$n getName] 1 }
  }
  foreach i [$b getInsts] { dict set ik [$i getName] [ot_prd_inst_key $i] }
  return [dict create sig $sig inst $ik wired $wired]
}
# nets to rip in block b against snapshot ref; -> dict {rip {net list} new n conn n moved n insts_changed n}
proc ot_prd_route_keep_select {b ref} {
  set rs [dict get $ref sig]; set ri [dict get $ref inst]
  set dirty [dict create]; set nch 0
  foreach i [$b getInsts] {
    set k [$i getName]
    if {[dict exists $ri $k] && [dict get $ri $k] eq [ot_prd_inst_key $i]} continue
    incr nch
    foreach t [$i getITerms] {
      set n [$t getNet]
      if {$n ne "NULL" && $n ne "" && [$n getSigType] ni {POWER GROUND}} { dict set dirty [$n getName] 1 }
    }
  }
  set rip {}; set nnew 0; set nconn 0; set nmv 0
  foreach n [$b getNets] {
    if {[$n getSigType] in {POWER GROUND}} continue
    set k [$n getName]
    if {![dict exists $rs $k]} { incr nnew; lappend rip $k; continue }
    if {[dict get $rs $k] ne [ot_prd_net_sig $n]} { incr nconn; lappend rip $k; continue }
    if {[dict exists $dirty $k]} { incr nmv; lappend rip $k }
  }
  return [dict create rip $rip new $nnew conn $nconn moved $nmv insts_changed $nch]
}
# FLOW-13 10-30 (R1route rerun on BTAB P4s15, CHECKED 5_1_grt.log): run BEFORE global_route -end_incremental.
# GlobalRouter::updateDirtyNets destroys the dbWire of EVERY net the session journaled dirty (rsz trial moves, resizes
# undone later, pin access resets, DPL), so in R1route 2754 reference routed nets had lost their wires before the
# selection ran (selected 1157, ripped 0).  Now: select + rip against the reference, then DETACH the wire of every other
# routed non-clock signal net (the wire stays in the block, unattached, so GRT finds no wire to destroy and keeps its
# guide); ot_prd_route_keep_restore re-attaches them after the incremental GRT.  Clock nets stay with clk_freeze
# (FIXED wires, ot_clk_freeze_assert restore).
proc ot_prd_route_keep {{ref_odb ""}} {
  if {$ref_odb eq ""} { set ref_odb $::env(RESULTS_DIR)/4_cts.odb }
  set b [ord::get_db_block]
  set rdb [odb::dbDatabase_create]
  if {[catch {odb::read_db $rdb $ref_odb} msg]} { error "OT_PRD_ROUTE_KEEP FAIL: cannot read reference $ref_odb: $msg" }
  set rb [[$rdb getChip] getBlock]
  set ref [ot_prd_route_snapshot $rb]
  odb::dbDatabase_destroy $rdb
  set nwref [dict size [dict get $ref wired]]
  if {!$nwref} { error "OT_PRD_ROUTE_KEEP FAIL: reference $ref_odb has no routed signal net (not a routed DB; use OT_PRD_FROM=grt)" }
  set sel [ot_prd_route_keep_select $b $ref]
  set clk [dict create]
  if {[llength [info commands ot_clk_dbnets]]} { foreach n [ot_clk_dbnets] { dict set clk [$n getName] 1 } }
  set nrip 0; set bad {}; set rip [dict create]
  foreach k [dict get $sel rip] {
    dict set rip $k 1
    if {[dict exists $clk $k]} { lappend bad $k; continue }
    set n [$b findNet $k]
    set w [$n getWire]
    if {$w ne "NULL"} { odb::dbWire_destroy $w; incr nrip }
  }
  if {[llength $bad]} { error "OT_PRD_ROUTE_KEEP FAIL: the ECO touched [llength $bad] frozen clock nets: [lrange $bad 0 9]" }
  set ::ot_prd_parked [dict create]
  foreach n [$b getNets] {
    if {[$n getSigType] in {POWER GROUND}} continue
    set k [$n getName]
    if {[dict exists $clk $k] || [dict exists $rip $k]} continue
    set w [$n getWire]
    if {$w eq "NULL" || $w eq ""} continue
    $w detach
    dict set ::ot_prd_parked $k $w
  }
  set ::ot_prd_keep_msg "OT_PRD_ROUTE_KEEP ripped $nrip nets ([llength [dict get $sel rip]] selected: new [dict get $sel new], connectivity\
 [dict get $sel conn], on moved/resized insts [dict get $sel moved]; insts changed [dict get $sel insts_changed])"
  puts "$::ot_prd_keep_msg; parked (detached) [dict size $::ot_prd_parked] kept routed wires through the incremental GRT"
  return $nrip
}
# after global_route -end_incremental: re-attach every parked wire (a wire GRT gave such a net meanwhile is replaced:
# the net's pins did not change, so its routed metal is the reference); reports the kept count vs the reference
proc ot_prd_route_keep_restore {} {
  set b [ord::get_db_block]
  set nre 0; set nrep 0
  dict for {k w} $::ot_prd_parked {
    set n [$b findNet $k]
    if {$n eq "NULL" || $n eq ""} { error "OT_PRD_ROUTE_KEEP FAIL: kept net $k vanished in the incremental GRT" }
    set cur [$n getWire]
    if {$cur ne "NULL" && $cur ne ""} { odb::dbWire_destroy $cur; incr nrep }
    $w attach $n
    if {[$n getWire] eq "NULL" || [$n getWire] eq ""} { error "OT_PRD_ROUTE_KEEP FAIL: cannot re-attach the routed wire of $k" }
    incr nre
  }
  set ::ot_prd_parked [dict create]
  set kept 0
  foreach n [$b getNets] { if {[$n getSigType] ni {POWER GROUND} && [$n getWire] ne "NULL"} { incr kept } }
  puts "OT_PRD_ROUTE_KEEP restore: re-attached $nre parked wires ($nrep replaced a GRT-time wire); kept routed $kept nets\
 (incl. frozen clock) after the incremental GRT"
  return $nre
}
