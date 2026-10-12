# el1011-q-coll 2026-10-11 22:45: qfd_io_collective cluster clock = the pre-placed balanced clock SPINE
# (physical/common_flow/clock_spine.tcl, el1011-hbm-attn c11a6e02a) in place of TritonCTS, with leaf targets = sink pin
# arrival + the hard child's own clock insertion (its TT lib max_clock_tree_path), every hard-macro clock pin its own
# leaf (OT_SPINE_MACRO_LEAF=1).  Why (pr2c-c5d3843bb, CLOCK LATENCY ACROSS THE HIERARCHY): TritonCTS built an 18-20
# level BUFx24 tree (insertion 541-650 ps TT) blind to the slices' internal 179-228 ps, so glue -> slice src seams fail
# FF hold (-11.5) and glue reg2reg carries 32 ps of launch/capture skew on the worst setup.
#
# OT_CTS_FIX_HOOKS member: list it FIRST.  The block's own PRE_CTS (qwen_die_masters/pre_cts_skew.tcl) is sourced before
# the fix hooks and wraps the real clock_tree_synthesis as ::qdm_cts_orig; the spine is spliced in UNDER it (it replaces
# ::qdm_cts_orig), so the io_ref boundary switch and every later fix hook still wrap the spine.
set ::icoll_child_ins [dict create]
if {[info exists ::env(ADDITIONAL_LIBS)]} {
  foreach lib $::env(ADDITIONAL_LIBS) {
    if {![file readable $lib]} continue
    set f [open $lib]; set txt [read $f]; close $f
    if {![regexp {cell\s*\(\s*"?([A-Za-z0-9_]+)"?\s*\)} $txt -> cell]} continue
    if {[regexp {max_clock_tree_path;\s*cell_rise\s*\(\s*scalar\s*\)\s*\{\s*values\s*\(\s*"([0-9.]+)"} $txt -> ins]} {
      dict set ::icoll_child_ins $cell $ins
    }
  }
}
set ::env(OT_SPINE_MACRO_LEAF) 1
if {![info exists ::env(OT_SPINE_PORT)] || $::env(OT_SPINE_PORT) eq ""} { set ::env(OT_SPINE_PORT) clk }
puts "ICOLL spine: child insertion targets $::icoll_child_ins (port $::env(OT_SPINE_PORT))"

set icoll_have_qdm [expr {[info procs ::qdm_cts_orig] ne ""}]
if {$icoll_have_qdm} {
  rename clock_tree_synthesis ::icoll_cts_outer
  rename ::qdm_cts_orig clock_tree_synthesis
}
source /src/physical/common_flow/clock_spine.tcl
if {$icoll_have_qdm} {
  rename clock_tree_synthesis ::qdm_cts_orig
  rename ::icoll_cts_outer clock_tree_synthesis
}

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
        if {[dict exists $::icoll_child_ins $m]} { set x [expr {$x + [dict get $::icoll_child_ins $m]}] }
      }
      if {$x > $v} { set v $x }
    }
    dict set a $n $v
  }
  return $a
}
