if {[info exists ::env(OT_PG_STRICT)] && $::env(OT_PG_STRICT) eq "1"} {
  set ot_pg_helper [file join [file dirname [info script]] native_pg_binding.tcl]
  if {[info exists ::env(OT_PG_HELPER)]} {set ot_pg_helper $::env(OT_PG_HELPER)} elseif {![file exists $ot_pg_helper]} {set ot_pg_helper /src/physical/common_flow/native_pg_binding.tcl}
  source $ot_pg_helper
  ot_pg_install_final_write_guard
  ot_pg_install_rc_observers
}
# [cg-hc] 2026-10-10: keep every clock-gate cell and the flop that drives its ENA as ONE instance (OT_CTS_FIX_HOOKS,
# sourced at PRE_CTS).  hfd_hc b9a0074bd hm10: the CTS-stage repair_timing CloneMove replicated the group ICG
# (clone_1_u_cg_0_0.u_cg.u_icg) to the leaves, so the ENREG flop placed beside the original gate drove far clones over
# 141 ps of wire into their early CK pins (gating check -652.6 ps).  With dont_touch the resizer cannot clone, move-swap or
# resize these cells; the ENA net is still buffered by repair_design if needed.  The BE r2 (nopush) recipe.  No constraint
# change.
proc ot_icg_dont_touch {} {
  set blk [ord::get_db_block]
  if {[expr {[info exists ::env(OT_PG_STRICT)] && $::env(OT_PG_STRICT) eq "1"}]} {set pg_mapping [ot_pg_prepare $blk]}
  set ng 0; set nf 0
  foreach i [$blk getInsts] {
    if {![string match "ICG*" [[$i getMaster] getName]]} continue
    if {![$i isDoNotTouch]} { if {[expr {[info exists ::env(OT_PG_STRICT)] && $::env(OT_PG_STRICT) eq "1"}]} {ot_pg_bind_before_protect $pg_mapping $i}; $i setDoNotTouch 1; incr ng }
    set ena [$i findITerm ENA]
    if {$ena eq "NULL" || $ena eq ""} continue
    set n [$ena getNet]
    if {$n eq "NULL" || $n eq ""} continue
    set d [$n getFirstOutput]
    if {$d eq "NULL" || $d eq ""} continue
    set di [$d getInst]
    if {[[$di getMaster] isSequential] && ![$di isDoNotTouch]} { if {[expr {[info exists ::env(OT_PG_STRICT)] && $::env(OT_PG_STRICT) eq "1"}]} {ot_pg_bind_before_protect $pg_mapping $di}; $di setDoNotTouch 1; incr nf }
  }
  puts "OT_ICG_DONT_TOUCH gates=$ng enable_flops=$nf"
}
ot_icg_dont_touch
