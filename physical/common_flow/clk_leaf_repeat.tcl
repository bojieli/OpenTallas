# HBM-CTS-LEAFSLEW (DIE-HBM-59, COORD 2026-11-02 23:2x): clock-tree level/leaf nets are repeated post-CTS, before the
# tap/leaf balance.  Why: TritonCTS buffers a branch only beyond -distance_between_buffers along its own H-tree
# segments, and -repair_clock_nets repairs only the ROOT wire (port -> root buffer).  A branch point in the core
# middle then drives its leaf buffers on the face rows with one unbuffered star wire (calendar_f20
# clknet_4_2__leaf_clk: BUFx24 at y 90 -> 5 leaf BUFx24 at y 6-8, 85-116 um, 40 fF wire): routed slew 325-340 ps at
# the leaf inputs > the 320-ps max_transition, and the post-route late ECO may not touch clock nets.  Same class on
# vmdel_lane_n (13 leaves, 323-382 ps).
# Rule (per clock net driven by a clock buffer/inverter, never the root port net): every load lies within
# OT_CLK_LEAF_MAX_UM (default 50 um, Manhattan) of its driver, and a net whose loads are all clock buffers/inverters
# drives at most OT_CLK_LEAF_MAX_FANOUT (default 12; 0 = no cap) of them.  A violating net gets one repeater per load
# group (greedy groups: the farthest load + every other far load within OT_CLK_LEAF_MAX_UM/2 of it, at most the fanout
# cap), placed half way between the driver and the group centroid, same master as the driver (clock buffers) else
# OT_CLK_LEAF_CELL; passes repeat until the rule holds (at most OT_CLK_LEAF_PASSES, default 6), then the cells are
# legalised.  The tap/leaf balance that runs after this hook sees the final tree, so tap insertion targets are
# unchanged.  No gate changes.  OT_CLK_LEAF_REPEAT=0 = off (old behaviour).  Then OT_CLR_NEXT_TCL is sourced.
# DIE-HBM-60/LEAFSLEW 11-03 slew gate (default on): the distance-only rule above repeated 30 nets on calendar_f20 and
# 12 on vmdel_lane_n; the extra stage on some leaves raised each tap tree's MAX sink, so the tap balance (pad capped at
# target + window - max) left the pin-register mean 22 ps short of the vclk bound (calendar FAIL_POSTCTS TT dev 22.1).
# Now a net is repeated only when its placement-estimated worst load slew exceeds OT_CLK_LEAF_SLEW_PS (default 80 ps;
# calendar 4_cts: the routed 340-ps net clknet_4_2__leaf_clk estimates 101 ps, every net that stayed < 320 routed
# estimates <= 118 ps; vmdel: the routed 323-382-ps net estimates 165 ps) AND it is a branch net (all loads clock
# buffers/inverters), or its estimate exceeds 2x the gate.  Inside such a net EVERY load goes behind a repeater
# (sibling leaves keep one common depth), grouped as above.  OT_CLK_LEAF_SLEW_PS=0 = the distance-only rule.
# KW-FIX-17 11-05 (COORD 16:4x): copied into the repo from die-hbm-66/forms/fhp12 as the default-on kit-wave class
# fix.  tools/autopilot/kit_wave.py stages this file into a relaunched kit whose routed TT sign-off showed max_slew
# violations on clock-tree cell / register clock pins (LEAFSLEW signature) and appends to its config.mk:
#   export OT_CLR_NEXT_TCL := $(POST_CTS_TCL)
#   override export POST_CTS_TCL = /work/clk_leaf_repeat.tcl
# so the kit's own POST_CTS_TCL hook (if any) still runs after this one.  An unset / empty OT_CLR_NEXT_TCL sources
# nothing; one naming this file itself is ignored (no recursion).
if {![info exists ::env(OT_CLK_LEAF_REPEAT)] || $::env(OT_CLK_LEAF_REPEAT) ne "0"} {
uplevel #0 {
  set clr_blk [ord::get_db_block]
  set clr_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
  set clr_max_um [expr {[info exists ::env(OT_CLK_LEAF_MAX_UM)] ? double($::env(OT_CLK_LEAF_MAX_UM)) : 50.0}]
  set clr_fo [expr {[info exists ::env(OT_CLK_LEAF_MAX_FANOUT)] ? int($::env(OT_CLK_LEAF_MAX_FANOUT)) : 12}]
  set clr_cell_default [expr {[info exists ::env(OT_CLK_LEAF_CELL)] ? $::env(OT_CLK_LEAF_CELL) : "BUFx16f_ASAP7_75t_R"}]
  set clr_passes [expr {[info exists ::env(OT_CLK_LEAF_PASSES)] ? int($::env(OT_CLK_LEAF_PASSES)) : 6}]
  set clr_slew_ps [expr {[info exists ::env(OT_CLK_LEAF_SLEW_PS)] ? double($::env(OT_CLK_LEAF_SLEW_PS)) : 80.0}]
  set clr_n_skip_slew 0
  proc clr_is_clkcell {inst} {
    set m [[$inst getMaster] getName]
    return [expr {[string match "BUF*" $m] || [string match "INV*" $m] || [string match "CKINV*" $m] || [string match "CLKBUF*" $m]}]
  }
  proc clr_xy {inst} {
    set b [$inst getBBox]
    return [list [expr {([$b xMin] + [$b xMax]) / 2}] [expr {([$b yMin] + [$b yMax]) / 2}]]
  }
  proc clr_is_clock_net {net} {
    if {[$net getSigType] eq "CLOCK"} { return 1 }
    return [string match "clknet*" [$net getName]]
  }
  # one net -> list of {driver_inst load_pairs} or "" when the net is not a repeatable clock-tree net
  proc clr_net {net} {
    if {[llength [$net getBTerms]]} { return "" }
    set drv ""; set loads {}
    foreach it [$net getITerms] {
      if {[$it isOutputSignal]} { if {$drv ne ""} { return "" }; set drv [$it getInst]; continue }
      if {[$it isInputSignal]} { lappend loads $it }
    }
    if {$drv eq "" || ![clr_is_clkcell $drv] || [llength $loads] == 0} { return "" }
    return [list $drv $loads]
  }
  set clr_n_nets 0; set clr_n_bufs 0; set clr_worst_before 0.0; set clr_worst_after 0.0; set clr_seq 0
  for {set clr_pass 1} {$clr_pass <= $clr_passes + 1} {incr clr_pass} {
    set clr_todo {}
    set clr_worst 0.0
    if {$clr_slew_ps > 0} { estimate_parasitics -placement }
    foreach net [$clr_blk getNets] {
      if {![clr_is_clock_net $net]} continue
      set r [clr_net $net]
      if {$r eq ""} continue
      lassign $r drv loads
      lassign [clr_xy $drv] dx dy
      set far {}; set all_clk 1
      foreach it $loads {
        lassign [clr_xy [$it getInst]] lx ly
        set d [expr {double(abs($lx - $dx) + abs($ly - $dy)) / $clr_dbu}]
        if {$d > $clr_worst} { set clr_worst $d }
        if {$d > $clr_max_um} { lappend far [list $it $lx $ly $d] }
        if {![clr_is_clkcell [$it getInst]]} { set all_clk 0 }
      }
      set over_fo [expr {$clr_fo > 0 && $all_clk && [llength $loads] > $clr_fo}]
      if {$clr_slew_ps > 0 && ([llength $far] || $over_fo)} {
        # slew gate: worst placement-estimated load slew (ps, user time units)
        set ms 0.0
        foreach it $loads {
          set pp [sta::find_pin "[[$it getInst] getName]/[[$it getMTerm] getName]"]
          if {$pp eq "" || $pp eq "NULL"} continue
          set s [get_property $pp slew_max]
          if {$s > $ms} { set ms $s }
        }
        if {$ms <= $clr_slew_ps || (!$all_clk && $ms <= 2.0 * $clr_slew_ps)} {
          if {$clr_pass == 1} { incr clr_n_skip_slew }
          continue
        }
        # balanced siblings: every load of the net goes behind a repeater
        set far {}
        foreach it $loads {
          lassign [clr_xy [$it getInst]] lx ly
          lappend far [list $it $lx $ly [expr {double(abs($lx - $dx) + abs($ly - $dy)) / $clr_dbu}]]
        }
        puts [format "OT_CLK_LEAF_REPEAT pass %d net %s est slew %.1f ps > %.0f, %d loads" $clr_pass [$net getName] $ms $clr_slew_ps [llength $loads]]
        set over_fo 0
      }
      if {[llength $far] || $over_fo} { lappend clr_todo [list $net $drv $loads $far $over_fo] }
    }
    if {$clr_pass == 1} { set clr_worst_before $clr_worst }
    set clr_worst_after $clr_worst
    puts [format "OT_CLK_LEAF_REPEAT pass %d: %d nets over rule (max %.0f um, fanout %d, slew gate %.0f ps), worst load distance %.1f um" \
            $clr_pass [llength $clr_todo] $clr_max_um $clr_fo $clr_slew_ps $clr_worst]
    if {![llength $clr_todo] || $clr_pass > $clr_passes} break
    foreach job $clr_todo {
      lassign $job net drv loads far over_fo
      lassign [clr_xy $drv] dx dy
      # load groups: far loads (distance rule), else (fanout rule only) every load, farthest first
      if {![llength $far]} {
        foreach it $loads { lassign [clr_xy [$it getInst]] lx ly; lappend far [list $it $lx $ly [expr {double(abs($lx-$dx)+abs($ly-$dy))/$clr_dbu}]] }
      }
      set far [lsort -real -decreasing -index 3 $far]
      set cap [expr {$clr_fo > 0 ? $clr_fo : 1000000}]
      set groups {}
      while {[llength $far]} {
        set seed [lindex $far 0]; set g [list $seed]; set rest {}
        foreach f [lrange $far 1 end] {
          if {[llength $g] < $cap && (abs([lindex $f 1] - [lindex $seed 1]) + abs([lindex $f 2] - [lindex $seed 2])) <= $clr_max_um * $clr_dbu / 2.0} {
            lappend g $f
          } else { lappend rest $f }
        }
        lappend groups $g; set far $rest
      }
      # a fanout-only split keeps one group on the driver when that alone meets the cap
      if {![llength [lindex $job 3]] && [llength $groups] == 1} continue
      # slew mode: one group close to the driver gains nothing from a repeater
      if {$clr_slew_ps > 0 && [llength $groups] == 1 && [lindex [lindex [lindex $groups 0] 0] 3] <= $clr_max_um} continue
      set m [[$drv getMaster] getName]
      set cell [expr {[string match "BUF*" $m] ? $m : $clr_cell_default}]
      foreach g $groups {
        set sx 0.0; set sy 0.0; set pins {}
        foreach f $g {
          set it [lindex $f 0]
          lappend pins [sta::find_pin "[[$it getInst] getName]/[[$it getMTerm] getName]"]
          set sx [expr {$sx + [lindex $f 1]}]; set sy [expr {$sy + [lindex $f 2]}]
        }
        set cx [expr {$sx / [llength $g]}]; set cy [expr {$sy / [llength $g]}]
        set px [expr {(($dx + $cx) / 2.0) / $clr_dbu}]; set py [expr {(($dy + $cy) / 2.0) / $clr_dbu}]
        incr clr_seq
        set nm "clkleafrep_${clr_seq}"
        # STA pin objects (odb names carry escaped bus brackets; sta::find_pin takes the odb name as is)
        if {[llength $pins] > 1} {
          insert_buffer -buffer_cell $cell -net [sta::db_net_to_sta $net] -load_pins $pins -location [list $px $py] \
            -buffer_name $nm -net_name "clknet_${nm}"
        } else {
          insert_buffer -buffer_cell $cell -load_pins $pins -location [list $px $py] -buffer_name $nm -net_name "clknet_${nm}"
        }
        set nn [$clr_blk findNet "clknet_${nm}"]
        if {$nn ne "NULL" && $nn ne ""} { $nn setSigType CLOCK }
        incr clr_n_bufs
      }
      incr clr_n_nets
    }
  }
  if {$clr_n_bufs} {
    detailed_placement
    check_placement -verbose
  }
  puts [format "OT_CLK_LEAF_REPEAT done: %d nets repeated, %d repeaters, worst load distance %.1f -> %.1f um (%d nets over distance kept: est slew <= gate)" \
          $clr_n_nets $clr_n_bufs $clr_worst_before $clr_worst_after $clr_n_skip_slew]
}
}
if {[info exists ::env(OT_CLR_NEXT_TCL)] && [string trim $::env(OT_CLR_NEXT_TCL)] ne ""
    && [file tail [string trim $::env(OT_CLR_NEXT_TCL)]] ne "clk_leaf_repeat.tcl"} {
  source [string trim $::env(OT_CLR_NEXT_TCL)]
}
