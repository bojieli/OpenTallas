# FLOW-20 11-01 (DIE-KV-60 01:21 ASK, COORD ruled): keep CTS-stage timing repair off the clock tree that CTS just built.
# Root cause (CHECKED, intel1 flow-20/reqcmp, KV kv3_phy V2 probe): a hard macro launch (u_core clk -> fh3 liberty arc)
# makes STA report the clk PORT as the startpoint, so the whole CTS tree (delaybuf_*_clk, clkbuf_*, wire*) lies on the
# "data" path that repair_timing walks.  UnbufferMove removed clock buffers, the journal restored them, and OpenSTA
# aborted in sta::RequiredCmp::requiredSet (vector index assert), deterministic, also with 1 thread.  With CTS buffers
# / inverters and CLOCK nets dont_touch for the repair call only: no assert, setup repair keeps its data-path moves and
# hold repair closes (+5 ps) instead of hitting RSZ-0060 max buffer count.  Clock DRV repair stays with CTS
# (-repair_clock_nets); dont_touch is released right after the call, so later stages are unchanged.
# Sourced from the kit PRE_CTS hook (pre_cts.tcl).  OT_CTS_REPAIR_PROTECT=0 restores the old behaviour.
proc ot_crp_protect {} {
  set blk [ord::get_db_block]
  set ni 0; set nn 0; set ::ot_crp_set {}
  foreach n [$blk getNets] {
    if {[$n getSigType] ne "CLOCK"} continue
    foreach it [$n getITerms] {
      if {![$it isOutputSignal]} continue
      set i [$it getInst]
      if {![regexp {^(BUF|INV|HB|CKINV|CKBUF)} [[$i getMaster] getName]] || [$i isDoNotTouch]} continue
      $i setDoNotTouch 1; lappend ::ot_crp_set $i; incr ni
    }
    if {![$n isDoNotTouch]} { $n setDoNotTouch 1; lappend ::ot_crp_set $n; incr nn }
  }
  puts "OT_CTS_REPAIR_PROTECT dont_touch clock buffers/inverters=$ni clock nets=$nn"
}
proc ot_crp_release {} {
  foreach o $::ot_crp_set { $o setDoNotTouch 0 }
  puts "OT_CTS_REPAIR_PROTECT released [llength $::ot_crp_set]"
  set ::ot_crp_set {}
}
if {!([info exists ::env(OT_CTS_REPAIR_PROTECT)] && $::env(OT_CTS_REPAIR_PROTECT) eq "0")
    && [info procs ::repair_timing_helper] ne "" && [info procs ::ot_crp_repair_timing_helper] eq ""} {
  rename ::repair_timing_helper ::ot_crp_repair_timing_helper
  proc ::repair_timing_helper {args} {
    ot_crp_protect
    set rc [catch {uplevel 1 [list ::ot_crp_repair_timing_helper {*}$args]} result opts]
    ot_crp_release
    return -options $opts $result
  }
  puts "OT_CTS_REPAIR_PROTECT installed"
} else {
  puts "OT_CTS_REPAIR_PROTECT off"
}
