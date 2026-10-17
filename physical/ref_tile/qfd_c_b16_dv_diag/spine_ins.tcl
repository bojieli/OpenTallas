# ref_tile cluster clock: the pre-placed balanced clock SPINE (physical/common_flow/clock_spine.tcl, el1011-hbm-attn
# c11a6e02a: attention halves leaf spread 1,634 -> 24 ps; idx w8 cluster 518 ps skew) replaces TritonCTS for the cluster
# clock.  Leaf target = arrival at the sink pin PLUS the hard child's own clock insertion (its TT lib max_clock_tree_path),
# so the spine balances the flops INSIDE the children against the cluster's own flops (CLOCK LATENCY ACROSS THE HIERARCHY).
set ::ot_ref_child_ins [dict create qfd_tile_nk_rp2_romleaf_rr/ck 235.0 qfd_tile_nk_rp2_romleaf_rr/ck_de 235.0 qfd_tile_nk_rp2_romleaf_rr/ck_dw 235.0 qfd_tile_nk_rp2_romleaf_rr/ck_fa0 235.0 qfd_tile_nk_rp2_romleaf_rr/ck_fa1 235.0 qfd_tile_nk_rp2_romleaf_rr/ck_fa2 235.0 qfd_tile_nk_rp2_romleaf_rr/ck_fa3 235.0 qfd_tile_nk_rp2_romleaf_rr/ck_fa4 235.0 qfd_tile_nk_rp2_romleaf_rr/ck_lsl0 235.0 qfd_tile_nk_rp2_romleaf_rr/ck_lsl1 235.0 qfd_tile_nk_rp2_romleaf_rr/ck_lsl2 235.0 qfd_tile_nk_rp2_romleaf_rr/ck_lsl3 235.0 qfd_tile_nk_rp2_romleaf_rr/ck_lsl4 235.0 qfd_tile_nk_rp2_romleaf_rr/ck_lsl5 235.0 qfd_tile_nk_rp2_romleaf_rr/ck_lsl6 235.0 qfd_tile_nk_rp2_romleaf_rr/ck_lsl7 235.0 qfd_tile_nk_rp2_romleaf_rr/ck_node 235.0 qfd_tile_nk_rp2_romleaf_rr/ck_rn 235.0 qfd_tile_nk_rp2_romleaf_rr/ck_rnw 235.0 qfd_tile_nk_rp2_romleaf_rr/ck_rp0 235.0 qfd_tile_nk_rp2_romleaf_rr/ck_rp1 235.0 qfd_tile_nk_rp2_romleaf_rr/ck_rp2 235.0 qfd_tile_nk_rp2_romleaf_rr/ck_rp3 235.0 qfd_tile_nk_rp2_romleaf_rr/ck_rp4 235.0 qfd_tile_nk_rp2_romleaf_rr/ck_rp5 235.0 qfd_tile_nk_rp2_romleaf_rr/ck_rp6 235.0 qfd_tile_nk_rp2_romleaf_rr/ck_rp7 235.0 qfd_tile_nk_rp2_romleaf_rr/ck_rp8 235.0 qfd_tile_nk_rp2_romleaf_rr/ck_rp9 235.0 qfd_tile_nk_rp2_romleaf_rr/ck_rs 235.0 qfd_tile_nk_rp2_romleaf_rr/ck_rsw 235.0 qfd_tile_nk_rp2_romleaf_rr/ck_tx0 235.0 qfd_tile_nk_rp2_romleaf_rr/ck_tx1 235.0 qfd_tile_nk_rp2_romleaf_rr/ck_tx2 235.0 qfd_tile_nk_rp2_romleaf_rr/ck_tx3 235.0 qfd_tile_nk_rp2_romleaf_rr/ck_tx4 235.0 qfd_tile_nk_rp2_romleaf_rr/ck_tx5 235.0 qfd_tile_nk_rp2_romleaf_rr/ck_tx6 235.0 qfd_tile_nk_rp2_romleaf_rr/ck_tx7 235.0 qfd_tile_nl_rp2_romleaf_rr/ck 235.0 qfd_tile_nl_rp2_romleaf_rr/ck_de 235.0 qfd_tile_nl_rp2_romleaf_rr/ck_dw 235.0 qfd_tile_nl_rp2_romleaf_rr/ck_fa2 235.0 qfd_tile_nl_rp2_romleaf_rr/ck_fa4 235.0 qfd_tile_nl_rp2_romleaf_rr/ck_lsl0 235.0 qfd_tile_nl_rp2_romleaf_rr/ck_lsl1 235.0 qfd_tile_nl_rp2_romleaf_rr/ck_lsl2 235.0 qfd_tile_nl_rp2_romleaf_rr/ck_lsl3 235.0 qfd_tile_nl_rp2_romleaf_rr/ck_lsl4 235.0 qfd_tile_nl_rp2_romleaf_rr/ck_lsl5 235.0 qfd_tile_nl_rp2_romleaf_rr/ck_lsl6 235.0 qfd_tile_nl_rp2_romleaf_rr/ck_lsl7 235.0 qfd_tile_nl_rp2_romleaf_rr/ck_rn 235.0 qfd_tile_nl_rp2_romleaf_rr/ck_rnw 235.0 qfd_tile_nl_rp2_romleaf_rr/ck_rp0 235.0 qfd_tile_nl_rp2_romleaf_rr/ck_rp1 235.0 qfd_tile_nl_rp2_romleaf_rr/ck_rp2 235.0 qfd_tile_nl_rp2_romleaf_rr/ck_rp3 235.0 qfd_tile_nl_rp2_romleaf_rr/ck_rp4 235.0 qfd_tile_nl_rp2_romleaf_rr/ck_rp5 235.0 qfd_tile_nl_rp2_romleaf_rr/ck_rp6 235.0 qfd_tile_nl_rp2_romleaf_rr/ck_rp7 235.0 qfd_tile_nl_rp2_romleaf_rr/ck_rp8 235.0 qfd_tile_nl_rp2_romleaf_rr/ck_rp9 235.0 qfd_tile_nl_rp2_romleaf_rr/ck_rs 235.0 qfd_tile_nl_rp2_romleaf_rr/ck_rsw 235.0 qfd_tile_nl_rp2_romleaf_rr/ck_tx0 235.0 qfd_tile_nl_rp2_romleaf_rr/ck_tx1 235.0 qfd_tile_nl_rp2_romleaf_rr/ck_tx2 235.0 qfd_tile_nl_rp2_romleaf_rr/ck_tx3 235.0 qfd_tile_nl_rp2_romleaf_rr/ck_tx4 235.0 qfd_tile_nl_rp2_romleaf_rr/ck_tx5 235.0 qfd_tile_nl_rp2_romleaf_rr/ck_tx6 235.0 qfd_tile_nl_rp2_romleaf_rr/ck_tx7 235.0]
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
