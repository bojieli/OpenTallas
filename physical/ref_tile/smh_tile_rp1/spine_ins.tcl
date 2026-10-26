# ref_tile cluster clock: the pre-placed balanced clock SPINE (physical/common_flow/clock_spine.tcl, el1011-hbm-attn
# c11a6e02a: attention halves leaf spread 1,634 -> 24 ps; idx w8 cluster 518 ps skew) replaces TritonCTS for the cluster
# clock.  Leaf target = arrival at the sink pin PLUS the hard child's own clock insertion (its TT lib max_clock_tree_path),
# so the spine balances the flops INSIDE the children against the cluster's own flops (CLOCK LATENCY ACROSS THE HIERARCHY).
set ::ot_ref_child_ins [dict create ot_hbm_accel_smh_bdc 200.1 ot_hbm_accel_smh_tcl 196.5 ot_hbm_accel_smh_tct 199.2 ot_hbm_accel_smh_xs 403.5 ot_smh_tr_group_beat_e 211.0]
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
puts "REF_TILE spine: child insertion targets $::ot_ref_child_ins"
