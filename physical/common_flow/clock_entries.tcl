# clock_entries.tcl -- strict hard-entry checks; hybrid_entries additionally builds declared glue roots.
#
# A WIRES-ONLY cluster has no register of its own, so it has no tree to build: every hard child takes its clock from
# its OWN port on the cluster face (RTL: port -> child clock pin, one net, one sink).  The die delivers phi - R_i at
# entry i, R_i = entry wire + the child's routed boundary insertion (views/<child>/insertion.json), so no child waits
# for the slowest one and the cluster adds no insertion of its own (a spine over 9 children measured 1.5 - 2.3 ns).
#
# Source it FIRST in pre_cts.tcl (the io_ref wrappers wrap this one).  It replaces clock_tree_synthesis by a check:
# every clock source port must drive exactly one hard-child clock pin and nothing else; a clock port that reaches a
# standard-cell register is an ERROR (that register belongs in a leaf).  Long entry wires (> OT_ENTRY_WIRE_MAX_UM,
# default 60) are reported: put the entry pin at the child's clock pin.
if {[info procs clock_tree_synthesis] ne "" && [info procs ot_ce_cts_orig] eq ""} {
  rename clock_tree_synthesis ot_ce_cts_orig
  proc clock_tree_synthesis {args} {
    set block [ord::get_db_block]
    set lim [expr {[info exists ::env(OT_ENTRY_WIRE_MAX_UM)] ? $::env(OT_ENTRY_WIRE_MAX_UM) : 60.0}]
    set dbu [expr {double([$block getDbUnitsPerMicron])}]
    set n 0; set bad 0; set far 0; set cts_nets {}; set cts_seen {}; set entry_nets {}
    set roots [expr {[info exists ::ot_ce_cts_roots] ? $::ot_ce_cts_roots : {}}]
    foreach clk [all_clocks] {
      foreach src [get_property $clk sources] {
        set pname [get_full_name $src]
        set bt [$block findBTerm $pname]
        if {$bt eq "NULL"} { puts "OT_ENTRIES ERROR: clock source $pname is not a top port"; incr bad; continue }
        set net [$bt getNet]
        if {$pname in $roots} {
          if {$pname in $cts_seen} { error "OT_HYBRID: duplicate CTS source $pname" }
          lappend cts_seen $pname
          set endpoints [get_fanout -flat -endpoints_only -from $src]
          set registers [all_registers -clock [get_full_name $clk] -clock_pins]
          if {![llength $registers]} { error "OT_HYBRID: CTS source $pname has no registers" }
          set regnames {}
          foreach pin $registers { lappend regnames [get_full_name $pin] }
          foreach pin $endpoints {
            set cell [get_cells -quiet -of_objects $pin]
            if {[llength $cell] != 1} { error "OT_HYBRID: CTS source $pname reaches a non-register endpoint" }
            # STA renders escaped identifiers differently from OpenDB names.
            # Convert the actual instance object rather than reparsing its name.
            set inst [sta::sta_to_db_inst [lindex $cell 0]]
            if {$inst eq "NULL" || [[$inst getMaster] isBlock] || [get_full_name $pin] ni $regnames} {
              error "OT_HYBRID: CTS source $pname must reach only standard-cell clock pins"
            }
          }
          lappend cts_nets [$net getName]
          continue
        }
        set sinks {}
        foreach it [$net getITerms] { if {[$it isInputSignal]} { lappend sinks $it } }
        if {[llength $sinks] != 1} {
          puts "OT_ENTRIES ERROR: clock entry $pname drives [llength $sinks] pins (one hard-child clock pin per entry)"
          incr bad; continue
        }
        set it [lindex $sinks 0]
        set inst [$it getInst]
        if {![[$inst getMaster] isBlock]} {
          puts "OT_ENTRIES ERROR: clock entry $pname drives [$inst getName]/[[$it getMTerm] getName] ([[$inst getMaster] getName]): not a hard child (a cluster register belongs in a leaf)"
          incr bad; continue
        }
        set pb [$bt getBBox]; set ib [$it getBBox]
        set d [expr {(abs(([$pb xMin] + [$pb xMax]) / 2 - ([$ib xMin] + [$ib xMax]) / 2)
                      + abs(([$pb yMin] + [$pb yMax]) / 2 - ([$ib yMin] + [$ib yMax]) / 2)) / $dbu}]
        if {$d > $lim} { incr far }
        lappend entry_nets [list $net $it]
        puts [format "OT_ENTRIES entry %s -> %s/%s (%s) wire %.1f um%s" $pname [$inst getName] [[$it getMTerm] getName] \
                  [[$inst getMaster] getName] $d [expr {$d > $lim ? " LONG" : ""}]]
        incr n
      }
    }
    if {$bad} { error "OT_ENTRIES: $bad clock entries are not port -> one hard-child clock pin" }
    if {[lsort $cts_seen] ne [lsort $roots]} { error "OT_HYBRID: declared CTS root coverage mismatch" }
    if {[llength $cts_nets]} {
      if {[lsearch -exact $args -clk_nets] >= 0} { error "OT_HYBRID: caller cannot override declared CTS nets" }
      # TritonCTS splits -clk_nets on whitespace (TritonCTS::setClockNets); a Tcl list braces bus-bit names
      # ({clk_outputs[0]}), which findNet never matches -> CTS-0056 (s81coll_calendar7 gate 10-15). Pass plain words.
      # TritonCTS -repair_clock_nets repairs ALL clock nets, including
      # excluded hard entries (observed clk_macro0 -> wire3581 -> SRAM).
      # Keep those entries as the required one-port/one-pin wire. CTS still
      # builds and balances the explicitly selected standard-cell roots;
      # ordinary timing and post-CTS ownership/insertion checks remain.
      set cts_args $args
      if {$n > 0 && [lsearch -exact $cts_args -repair_clock_nets] >= 0} {
        set cts_args {}
        foreach arg $args {if {$arg ne "-repair_clock_nets"} {lappend cts_args $arg}}
        puts "OT_HYBRID excluded hard entries: in-CTS -repair_clock_nets disabled; selected-root trees repaired after CTS"
      }
      ot_ce_cts_orig {*}$cts_args -clk_nets [join $cts_nets " "]
      # Without long-wire repair the selected-root trees keep unbuffered leaf hops (qfd_tt_head_static h4 gate
      # 10-15: a 300 um clkbuf_6_63__f -> leaf_193 hop added 266 ps, insertion 535.9 / spread 245.8 ps).  Repair
      # the trees AFTER CTS with every hard entry net marked do-not-touch, then prove each entry is still the one
      # port -> one hard-child clock pin wire (fail closed).
      if {[llength $cts_args] != [llength $args]} {
        set ot_ce_prev {}
        foreach e $entry_nets { set en [lindex $e 0]; lappend ot_ce_prev [$en isDoNotTouch]; $en setDoNotTouch 1 }
        repair_clock_nets
        foreach e $entry_nets p $ot_ce_prev {
          set en [lindex $e 0]; $en setDoNotTouch $p
          set its {}
          foreach it [$en getITerms] { if {[$it isInputSignal]} { lappend its $it } }
          if {[llength $its] != 1 || [lindex $its 0] ne [lindex $e 1]} {
            error "OT_HYBRID: post-CTS clock repair changed hard entry net [$en getName]"
          }
        }
        puts "OT_HYBRID post-CTS repair_clock_nets on selected roots; [llength $entry_nets] hard entries unchanged"
      }
      puts "OT_HYBRID CTS roots [join $roots " "]; hard-child entries excluded"
    }
    if {[llength $cts_nets]} {
      puts "OT_ENTRIES done: $n independent hard entries, [llength $cts_nets] glue CTS roots, $far entry wires over $lim um"
    } else {
      puts "OT_ENTRIES done: $n clock entries, no tree built, $far entry wires over $lim um"
    }
  }
}
