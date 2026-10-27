# Plan-built core clock tree at the ORFS CTS step (S81-CORE-LAT-R12; root cause of ODB-0370 in the R10 l0r builds).
# master_core_infra.tcl (core_infra.tcl) builds the master-plan tree before GPL: fixed dont_touch cells, every planned
# net dont_touch, only the plan's CTS-open nets (leaf / gated-domain nets below a planned stage) left buildable.
# TritonCTS does not honour dont_touch NETS: run on the core clock it walks the whole planned tree, re-clusters every
# planned net with >1 sink and stops on the first planned buffer it must disconnect ("ODB-0370 Attempt to disconnect
# term A of dont_touch instance mp_ck_T1_br", R10 std + NDR).  Structural rule (12.7c/12.8a-b: the plan owns the
# tree): TritonCTS builds ONLY the CTS-open nets; a leaf-complete plan tree is not re-synthesised.
# Fail-closed: the CTS-open count must equal the plan's, and every register clock pin must sit on a planned
# (dont_touch) net or on a CTS-open net driven by a planned cell.  Sourced from the kit PRE_CTS hook.
if {![llength [info commands ::ot_ci_tritoncts]]} {
  rename ::clock_tree_synthesis ::ot_ci_tritoncts
  proc ::clock_tree_synthesis {args} {
    set blk [ord::get_db_block]
    set open {}
    foreach n [$blk getNets] {
      if {[$n getSigType] ne "CLOCK" || [$n isDoNotTouch]} continue
      set drv [$n getFirstOutput]
      if {$drv eq "NULL" || $drv eq "" || ![[$drv getInst] isDoNotTouch]} continue
      lappend open [$n getName]
    }
    if {[llength $open] != $::ot_ci_cts_plan_open} {
      error "OT_CORE_INFRA_CTS_OPEN_COUNT [llength $open] CTS-open nets driven by planned cells != plan $::ot_ci_cts_plan_open"
    }
    set nck 0; set bad {}
    foreach p [all_registers -clock_pins] {
      set it [sta::sta_to_db_pin $p]
      if {$it eq "NULL" || $it eq ""} continue
      incr nck
      set n [$it getNet]
      if {$n eq "NULL" || !([$n isDoNotTouch] || [lsearch -exact $open [$n getName]] >= 0)} {
        lappend bad "[[$it getInst] getName]/[[$it getMTerm] getName]"
      }
    }
    if {[llength $bad]} {error "OT_CORE_INFRA_CTS_UNPLANNED_CLOCK_PINS [llength $bad]: [lrange $bad 0 9]"}
    if {![llength $open]} {
      puts "OT_CORE_INFRA_CTS leaf-complete plan tree: $nck register clock pins on planned dont_touch nets; TritonCTS not run"
      return
    }
    puts "OT_CORE_INFRA_CTS TritonCTS on [llength $open] CTS-open nets only; $nck register clock pins checked"
    set a {}; set skip 0
    foreach x $args {
      if {$skip} {set skip 0; continue}
      if {$x eq "-clk_nets"} {set skip 1; continue}
      lappend a $x
    }
    ::ot_ci_tritoncts {*}$a -clk_nets $open
  }
}
