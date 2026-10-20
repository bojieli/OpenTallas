# ref_tile cluster clock: the pre-placed balanced clock SPINE (physical/common_flow/clock_spine.tcl, el1011-hbm-attn
# c11a6e02a: attention halves leaf spread 1,634 -> 24 ps; idx w8 cluster 518 ps skew) replaces TritonCTS for the cluster
# clock.  Leaf target = arrival at the sink pin PLUS the hard child's own clock insertion (its TT lib max_clock_tree_path),
# so the spine balances the flops INSIDE the children against the cluster's own flops (CLOCK LATENCY ACROSS THE HIERARCHY).
set ::ot_ref_child_ins [dict create ot_hgi_coll_ctl_v5_q2/clk_control 203.4 ot_hgi_coll_fj_q2/clk 136.0 ot_hgi_coll_pring_static_state_capture_lane/clk 126.7 ot_hgi_coll_qslots_capture_pin_v2/clk 103.9 ot_hgi_coll_qso_q2_b1/clk 84.0 ot_hgi_coll_qso_q2_b32/clk 107.9 ot_hgi_coll_ring_ag_ctl/clk 180.7 ot_hgi_coll_static_vmwrite_roots_v6_physical/clk_bank0 80.4 ot_hgi_coll_static_vmwrite_roots_v6_physical/clk_bank1 79.9 ot_hgi_coll_static_vmwrite_roots_v6_physical/clk_bank2 81.6 ot_hgi_coll_static_vmwrite_roots_v6_physical/clk_bank3 81.4 ot_hgi_coll_static_vmwrite_roots_v6_physical/clk_bank4 81.0 ot_hgi_coll_static_vmwrite_roots_v6_physical/clk_bank5 81.1 ot_hgi_coll_static_vmwrite_roots_v6_physical/clk_bank6 79.2 ot_hgi_coll_static_vmwrite_roots_v6_physical/clk_bank7 78.3 ot_hgi_coll_static_vmwrite_roots_v6_physical/clk_body 251.1 ot_hgi_coll_static_vmwrite_roots_v6_physical/clk_meta 52.2 ot_hgi_coll_static_vmwrite_roots_v6_physical/clk_rgx_ctrl 77.2 ot_hgi_coll_static_vmwrite_roots_v6_physical/clk_rgx_data0 90.9 ot_hgi_coll_static_vmwrite_roots_v6_physical/clk_rgx_data1 93.3 ot_hgi_coll_static_vmwrite_roots_v6_physical/clk_rgx_data2 89.2 ot_hgi_coll_static_vmwrite_roots_v6_physical/clk_rgx_data3 88.4 ot_hgi_coll_static_vmwrite_roots_v6_physical/clk_tkw 90.8]
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
        regexp {[^/]+$} [get_full_name $pin] pn
        if {[dict exists $::ot_ref_child_ins "$m/$pn"]} { set m "$m/$pn" }
        if {[dict exists $::ot_ref_child_ins $m]} { set x [expr {$x + [dict get $::ot_ref_child_ins $m]}] }
      }
      if {$x > $v} { set v $x }
    }
    dict set a $n $v
  }
  return $a
}
puts "REF_TILE spine: child insertion targets $::ot_ref_child_ins"
