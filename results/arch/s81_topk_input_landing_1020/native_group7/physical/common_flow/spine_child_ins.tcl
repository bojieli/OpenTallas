# spine_child_ins.tcl (el1011-hbm-attn 2026-10-12): CLOCK LATENCY ACROSS THE HIERARCHY for hand-flow clusters that use
# physical/common_flow/clock_spine.tcl (same mechanism as tools/ref_tile spine_ins.tcl, but the targets come from the
# environment so the route reads them from the ACTUAL child views it links): leaf target = arrival at the sink pin PLUS
# the hard child's own clock-pin insertion (its TT lib max_clock_tree_path), so the spine balances the flops INSIDE the
# children against each other and the cluster's own flops.  Chain it right AFTER clock_spine.tcl in OT_CTS_FIX_HOOKS and
# set OT_SPINE_MACRO_LEAF=1 (each hard-child clock pin its own leaf).  Env: OT_SPINE_CHILD_INS = "master ps master ps ..."
# (written by tools/closure_loop/child_ins_env.py from the child TT libs; forwarded by run_abi3_physical.py).
set ::ot_ref_child_ins [dict create]
if {[info exists ::env(OT_SPINE_CHILD_INS)]} {
  foreach {m v} $::env(OT_SPINE_CHILD_INS) { dict set ::ot_ref_child_ins $m $v }
}
if {[dict size $::ot_ref_child_ins] == 0} { error "spine_child_ins.tcl: OT_SPINE_CHILD_INS empty (no child insertion targets)" }
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
        set m [get_property $c ref_name]
        if {[dict exists $::ot_ref_child_ins $m]} { set x [expr {$x + [dict get $::ot_ref_child_ins $m]}] }
      }
      if {$x > $v} { set v $x }
    }
    dict set a $n $v
  }
  return $a
}
puts "OT_SPINE child insertion targets: $::ot_ref_child_ins"
