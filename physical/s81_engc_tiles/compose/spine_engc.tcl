# dsfd_engram_c cluster clock (el1013-s81-engram 2026-10-13): the pre-placed balanced SPINE of
# physical/common_flow/clock_spine.tcl (one leaf per child clock pin, OT_SPINE_MACRO_LEAF=1) in place of TritonCTS + the
# per-child delay chains.  Listed FIRST in OT_CTS_FIX_HOOKS.  Leaf target = clock-pin arrival + the child's TARGET below:
# its internal insertion (TT liberty max_clock_tree_path) plus the entry offset solved from the measured launch -> capture
# pair slacks of the balanced run (gate/spine_solve.py; 0 = plain balance).  Per INSTANCE (pb0 / pb2 share a master).
source /src/physical/common_flow/clock_spine.tcl
set ::ot_engc_ck_target [dict create u_win 181.8 u_io 280.5 u_ws 297.1 u_pb1 461.6 u_pb0 453.8 u_pb2 453.8 u_lkp 366.7 u_sink 282.0]
set ::ot_engc_ck_offset [dict create u_win -30 u_io 0 u_ws -30 u_pb1 10 u_pb0 -10 u_pb2 0 u_lkp 0 u_sink 0]
proc ot_sp_leaf_arrivals {} {
  estimate_parasitics -placement
  sta::find_timing_paths -path_delay max -group_path_count 1
  set a [dict create]
  dict for {n net} $::ot_sp_leafnet {
    set v 0.0
    foreach pin [get_pins -quiet -of_objects [get_nets -quiet [$net getName]] -filter "direction==input"] {
      set x [get_property $pin arrival_max_rise]
      if {$x eq "" || $x eq "INF" || $x eq "-INF"} continue
      set c [get_cells -quiet -of_objects $pin]
      if {[llength $c]} {
        set m [get_full_name $c]
        if {[dict exists $::ot_engc_ck_target $m]} { set x [expr {$x + [dict get $::ot_engc_ck_target $m] - [dict get $::ot_engc_ck_offset $m]}] }
      }
      if {$x > $v} { set v $x }
    }
    dict set a $n $v
  }
  return $a
}
puts "ENGC spine: per-child targets $::ot_engc_ck_target offsets $::ot_engc_ck_offset"
# The reset conditioner must see the SAME branch as the macro clock pin.
# Temporarily remove its clocks from spine binning (which intentionally gives
# ordinary top flops separate leaves), then reconnect to the child's leaf net.
rename clock_tree_synthesis ot_engc_spine_cts
proc clock_tree_synthesis {args} {
  set b [ord::get_db_block]; set reconnect {}
  foreach child {win io ws pb1 pb0 pb2 lkp sink} {
    foreach i [$b getInsts] {
      if {![string match *u_rst_${child}* [$i getName]]} continue
      foreach it [$i getITerms] {
        set mt [$it getMTerm]
        if {[$mt getSigType] ne "CLOCK" && [$mt getName] ni {CLK CK CP}} continue
        lappend reconnect [list $child $it]
        $it disconnect
      }
    }
  }
  if {[llength $reconnect] < 16} { error "ENGC reset sync clocks missing: [llength $reconnect] < 16" }
  ot_engc_spine_cts {*}$args
  foreach row $reconnect {
    lassign $row child it
    set macro [$b findInst u_$child]
    set net [[$macro findITerm ck] getNet]
    if {$net eq "NULL"} { error "ENGC macro clock disconnected: $child" }
    # Spine completion protects its leaf nets; open only this branch while
    # adding the two local reset clocks, then restore the same protection.
    $net setDoNotTouch 0
    [$it getInst] setDoNotTouch 0
    $it connect $net
    [$it getInst] setDoNotTouch 1
    $net setDoNotTouch 1
    puts "ENGC reset clock [[$it getInst] getName]/[[$it getMTerm] getName] = u_${child}/ck net [$net getName]"
  }
  estimate_parasitics -placement
}
