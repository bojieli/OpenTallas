# el1011-ds-mtp 2026-10-12: clock SPINE (physical/common_flow/clock_spine.tcl) for a cluster of HARD children whose own clock
# insertion is large, generalised from el1011-q-coll's icoll_spine.tcl without the qwen pre_cts_skew splice.
# Leaf target = latest sink pin arrival + that sink's hard-child insertion (its TT lib max_clock_tree_path, read from
# ADDITIONAL_LIBS); every hard-macro clock pin is its own leaf (OT_SPINE_MACRO_LEAF=1).  The spine pads the flop leaves until
# they arrive with the children's INTERNAL flops, so glue -> child seams see no launch/capture skew of the child insertion
# (dsfd_mtp_hrow: 30 banks at 475 ps TT internal insertion, 140,653 glue flops on ck[0]).
# OT_CTS_FIX_HOOKS member: list it FIRST (it wraps clock_tree_synthesis; later hooks wrap it).
set ::ot_spci_ins [dict create]
if {[info exists ::env(ADDITIONAL_LIBS)]} {
  foreach lib $::env(ADDITIONAL_LIBS) {
    if {![file readable $lib]} continue
    set f [open $lib]; set txt [read $f]; close $f
    if {![regexp {cell\s*\(\s*"?([A-Za-z0-9_]+)"?\s*\)} $txt -> cell]} continue
    if {[regexp {max_clock_tree_path;\s*cell_rise\s*\(\s*scalar\s*\)\s*\{\s*values\s*\(\s*"([0-9.]+)"} $txt -> ins]} {
      dict set ::ot_spci_ins $cell $ins
    }
  }
}
set ::env(OT_SPINE_MACRO_LEAF) 1
puts "OT_SPINE child insertion targets: $::ot_spci_ins"
source /src/physical/common_flow/clock_spine.tcl

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
        if {[dict exists $::ot_spci_ins $m]} { set x [expr {$x + [dict get $::ot_spci_ins $m]}] }
      }
      if {$x > $v} { set v $x }
    }
    dict set a $n $v
  }
  return $a
}
