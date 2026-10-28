# Plan-built core clock tree at the ORFS CTS step (S81-CORE-LAT-R12; root cause of ODB-0370 in the R10 l0r builds).
# master_core_infra.tcl (core_infra.tcl) builds the master-plan tree before GPL: fixed dont_touch cells, every planned
# net dont_touch, only the plan's CTS-open nets (leaf / gated-domain nets below a planned stage) left buildable.
# TritonCTS does not honour dont_touch NETS: run on the core clock it walks the whole planned tree, re-clusters every
# planned net with >1 sink and stops on the first planned buffer it must disconnect ("ODB-0370 Attempt to disconnect
# term A of dont_touch instance mp_ck_T1_br", R10 std + NDR).  Structural rule (12.7c/12.8a-b: the plan owns the
# tree): TritonCTS builds ONLY the CTS-open nets; a leaf-complete plan tree is not re-synthesised.
# Fail-closed: the CTS-open count must equal the plan's, and every register clock pin must sit on a planned
# (dont_touch) net or on a CTS-open net driven by a planned cell.  Sourced from the kit PRE_CTS hook.
# FLOW-GEN-2 opt-in (core_tree.post_place_rebind = "exact_count", emit_cts_tcl sets ::ot_ci_leaf_rebind_leaves):
# GPL moves the flops after the plan bound them to leaves; before CTS every movable sink of the listed REGISTER
# leaves (same clock, same plan depth) is re-bound so each leaf keeps EXACTLY its planned sink count at minimum total
# squared sink->leaf distance (core_leaf_rebind.py).  Same port, same buffer depth -> clock function unchanged.
proc ot_ci_leaf_rebind {} {
  set blk [ord::get_db_block]
  set u [[ord::get_db_tech] getDbUnitsPerMicron]
  set dir [expr {[info exists ::env(RESULTS_DIR)] ? $::env(RESULTS_DIR) : [pwd]}]
  set py [expr {[info exists ::ot_ci_leaf_rebind_py] ? $::ot_ci_leaf_rebind_py : "/work/core_leaf_rebind.py"}]
  set pinned [dict create]
  if {[info exists ::ot_ci_leaf_rebind_pinned]} {foreach p $::ot_ci_leaf_rebind_pinned {dict set pinned $p 1}}
  set nets [dict create]; set before [dict create]; set its {}
  set fin [open $dir/core_leaf_rebind_in.tsv w]
  foreach leaf $::ot_ci_leaf_rebind_leaves {
    set i [$blk findInst $leaf]
    if {$i eq "NULL" || ![$i isDoNotTouch]} {close $fin; error "OT_CORE_LEAF_REBIND_LEAF $leaf is not a planned cell"}
    set n [[$i getFirstOutput] getNet]
    if {$n eq "NULL" || ![$n isDoNotTouch] || [$n getSigType] ne "CLOCK"} {
      close $fin; error "OT_CORE_LEAF_REBIND_NET $leaf output is not a planned dont_touch clock net"
    }
    dict set nets $leaf $n
    set b [$i getBBox]
    puts $fin [format "L %s %.4f %.4f" $leaf [expr {([$b xMin]+[$b xMax])/2.0/$u}] [expr {([$b yMin]+[$b yMax])/2.0/$u}]]
    set k 0
    foreach it [$n getITerms] {
      if {![$it isInputSignal]} continue
      set b [[$it getInst] getBBox]
      set nm "[[$it getInst] getName]/[[$it getMTerm] getName]"
      puts $fin [format "S %d %.4f %.4f %s %d" [llength $its] [expr {([$b xMin]+[$b xMax])/2.0/$u}] \
                   [expr {([$b yMin]+[$b yMax])/2.0/$u}] $leaf [dict exists $pinned $nm]]
      lappend its $it; incr k
    }
    dict set before $leaf $k
  }
  close $fin
  if {[catch {exec python3 -I $py $dir/core_leaf_rebind_in.tsv $dir/core_leaf_rebind.tsv} msg]} {
    error "OT_CORE_LEAF_REBIND_FAILED $msg"
  }
  set moves {}; set summ ""
  set fh [open $dir/core_leaf_rebind.tsv]
  foreach line [split [read $fh] "\n"] {
    if {[string match "# *" $line]} {set summ [string range $line 2 end]; continue}
    if {[regexp {^M (\d+) (\S+) (\S+)$} $line -> k from to]} {
      set it [lindex $its $k]
      if {![dict exists $nets $from] || ![dict exists $nets $to] || [$it getNet] ne [dict get $nets $from]} {
        close $fh; error "OT_CORE_LEAF_REBIND_MOVE $line does not match the planned binding"
      }
      lappend moves $it [dict get $nets $to]
    }
  }
  close $fh
  dict for {leaf n} $nets {$n setDoNotTouch 0}
  try {
    foreach {it n} $moves {
      set inst [$it getInst]; set protected [$inst isDoNotTouch]
      if {$protected} {$inst setDoNotTouch 0}
      try {$it disconnect; $it connect $n} finally {if {$protected} {$inst setDoNotTouch 1}}
    }
  } finally {
    dict for {leaf n} $nets {$n setDoNotTouch 1}
  }
  dict for {leaf n} $nets {
    set k 0
    foreach it [$n getITerms] {if {[$it isInputSignal]} {incr k}}
    if {$k != [dict get $before $leaf]} {error "OT_CORE_LEAF_REBIND_COUNT $leaf $k != planned [dict get $before $leaf]"}
  }
  puts "$summ applied=[expr {[llength $moves]/2}] (leaf counts unchanged; record $dir/core_leaf_rebind.tsv)"
}
if {![llength [info commands ::ot_ci_tritoncts]]} {
  rename ::clock_tree_synthesis ::ot_ci_tritoncts
  proc ::clock_tree_synthesis {args} {
    if {[info exists ::ot_ci_leaf_rebind_leaves]} {ot_ci_leaf_rebind}
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
