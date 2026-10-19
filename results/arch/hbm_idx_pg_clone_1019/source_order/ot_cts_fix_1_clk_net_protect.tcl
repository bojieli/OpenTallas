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
  set k 0; set j 0
  foreach n [$blk getNets] {
    if {[$n getSigType] ne "CLOCK"} continue
    if {![$n isDoNotTouch]} { $n setDoNotTouch 1; incr k }
    set d [$n getFirstOutput]
    if {$d ne "NULL" && $d ne ""} {
      set i [$d getInst]
      if {[regexp {^(clkbuf|delaybuf|clkload|wire|max_length|ot_fclk_root_buf)} [$i getName]] && ![$i isDoNotTouch]} { $i setDoNotTouch 1; incr j }
    }
  }
  puts "OT_CLK_PROTECT dont_touch clock nets=$k clock buffers=$j"
}
if {[info procs repair_timing_helper] ne "" && [info procs ot_cp_repair_timing_helper] eq ""} {
  rename repair_timing_helper ot_cp_repair_timing_helper
  proc repair_timing_helper {args} {
    ot_protect_clock_tree
    ot_cp_repair_timing_helper {*}$args
  }
}
