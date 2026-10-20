# PG binding is required before protection in standard mode too. This is a
# source-owned CTS boundary, not a native birth-callback capability.
set ot_pg_helper [file join [file dirname [info script]] native_pg_binding.tcl]
if {[info exists ::env(OT_PG_HELPER)]} {set ot_pg_helper $::env(OT_PG_HELPER)} elseif {![file exists $ot_pg_helper]} {set ot_pg_helper /src/physical/common_flow/native_pg_binding.tcl}
source $ot_pg_helper
ot_pg_install_final_write_guard
ot_pg_install_rc_observers
ot_pg_install_unsupported_birth_guards

# CLAUDE setup-triage 2026-10-07: keep data-path timing repair off the clock tree.
#
# Triage evidence (setup-triage.md, hfd_svc_SE_s5 r18, -167 ps): the CTS-stage repair_timing in cts.tcl inserted
# rebuffer51170 / rebuffer51169 on the CAPTURE clock path (verified in 4_1_cts.odb; absent in 3_place.odb) and that
# path no longer passes through the six-deep balance chain clkbuf_1_x_0..5 that the launch path still crosses:
# launch 848 ps vs capture 543 ps (+305 ps wrong-sign skew).  This hook marks every net CTS built (sig type CLOCK) and
# every CTS buffer dont_touch before each repair_timing_helper call, so resizer moves (rebuffer, buffer removal,
# cloning) cannot restructure a balanced tree.  Clock-net DRV repair stays with CTS (-repair_clock_nets) and the
# later repair_clock_nets / repair_design calls (dont_touch only binds resizer timing moves).  Constraints unchanged.
proc ot_protect_clock_tree {} {
  set blk [ord::get_db_block]
  if {[ot_pg_strict_enabled]} {
    ot_pg_require_cts_placement_context
    # Include open-output CTS loads, port/hold cells and physical-only masters.
    # This fixes protection ordering; native CTS may already have estimated RC
    # internally. The explicit refresh below establishes only new placement RC.
    set pg_bound [ot_pg_bind_batch_before_protect $blk [$blk getInsts]]
    ot_pg_assert_all_native $blk [ot_pg_prepare $blk]
  } else {
    set pg_bound [ot_pg_standard_bind protect_clock_tree]
  }
  set k 0; set j 0
  foreach n [$blk getNets] {
    if {[$n getSigType] ne "CLOCK"} continue
    set d [$n getFirstOutput]
    if {$d ne "NULL" && $d ne ""} {
      set i [$d getInst]
      if {[regexp {^(clkbuf|delaybuf|clkload|wire|max_length|ot_fclk_root_buf)} [$i getName]] && ![$i isDoNotTouch]} { $i setDoNotTouch 1; incr j }
    }
    if {![$n isDoNotTouch]} { $n setDoNotTouch 1; incr k }
  }
  # PG metadata changes invalidate an already estimated parasitics state. CTS
  # invokes this hook immediately before timing repair, after its own estimate.
  if {[ot_pg_strict_enabled] && [info exists ::ot_pg_bindings_dirty] && $::ot_pg_bindings_dirty > 0} {
    # Earlier hooks may have changed bindings even when this hook adds none.
    ot_pg_require_cts_placement_context
    estimate_parasitics -placement
  }
  puts "OT_CLK_PROTECT dont_touch clock nets=$k clock buffers=$j pg_bound=$pg_bound scope=source_cts_before_protect"
}
if {[info procs repair_timing_helper] ne "" && [info procs ot_cp_repair_timing_helper] eq ""} {
  rename repair_timing_helper ot_cp_repair_timing_helper
  proc repair_timing_helper {args} {
    ot_protect_clock_tree
    set result [ot_cp_repair_timing_helper {*}$args]
    if {![ot_pg_strict_enabled]} {return $result}
    # Repair inserts non-clock hold/setup cells. Bind the complete native cohort
    # before the caller's next report/checkpoint and explicitly re-estimate RC.
    # This does not cover analysis performed INSIDE the native repair command.
    ot_pg_require_cts_placement_context
    set block [ord::get_db_block]
    set bound [ot_pg_bind_batch_before_protect $block [$block getInsts]]
    if {$::ot_pg_bindings_dirty > 0} {estimate_parasitics -placement}
    ot_pg_assert_all_native $block [ot_pg_prepare $block]
    puts "OT_PG_POST_REPAIR bound=$bound scope=source_cts_return_boundary"
    return $result
  }
}
