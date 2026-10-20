# ref_tile cluster clock: the pre-placed balanced clock SPINE (physical/common_flow/clock_spine.tcl, el1011-hbm-attn
# c11a6e02a: attention halves leaf spread 1,634 -> 24 ps; idx w8 cluster 518 ps skew) replaces TritonCTS for the cluster
# clock.  Leaf target = arrival at the sink pin PLUS the hard child's own clock insertion (its TT lib max_clock_tree_path),
# so the spine balances the flops INSIDE the children against the cluster's own flops (CLOCK LATENCY ACROSS THE HIERARCHY).
set ::ot_ref_child_ins [dict create qfd_c_stn514/ck 114.0 qfd_c_stn516/ck 114.0 qfd_c_xstn/ck 114.0 qfd_c_xstnw/ck 114.0 qfd_tile_nk_rp2_romleaf_rr/ck 190.5 qfd_tile_nk_rp2_romleaf_rr/ck_de 150.0 qfd_tile_nk_rp2_romleaf_rr/ck_dw 150.0 qfd_tile_nk_rp2_romleaf_rr/ck_fa0 150.0 qfd_tile_nk_rp2_romleaf_rr/ck_fa1 150.0 qfd_tile_nk_rp2_romleaf_rr/ck_fa2 150.0 qfd_tile_nk_rp2_romleaf_rr/ck_fa3 150.0 qfd_tile_nk_rp2_romleaf_rr/ck_fa4 150.0 qfd_tile_nk_rp2_romleaf_rr/ck_lsl0 176.7 qfd_tile_nk_rp2_romleaf_rr/ck_lsl1 176.7 qfd_tile_nk_rp2_romleaf_rr/ck_lsl2 176.7 qfd_tile_nk_rp2_romleaf_rr/ck_lsl3 176.7 qfd_tile_nk_rp2_romleaf_rr/ck_lsl4 176.7 qfd_tile_nk_rp2_romleaf_rr/ck_lsl5 176.7 qfd_tile_nk_rp2_romleaf_rr/ck_lsl6 176.7 qfd_tile_nk_rp2_romleaf_rr/ck_lsl7 176.7 qfd_tile_nk_rp2_romleaf_rr/ck_node 267.6 qfd_tile_nk_rp2_romleaf_rr/ck_rn 150.0 qfd_tile_nk_rp2_romleaf_rr/ck_rnw 150.0 qfd_tile_nk_rp2_romleaf_rr/ck_rp0 228.1 qfd_tile_nk_rp2_romleaf_rr/ck_rp1 228.1 qfd_tile_nk_rp2_romleaf_rr/ck_rp2 228.1 qfd_tile_nk_rp2_romleaf_rr/ck_rp3 228.1 qfd_tile_nk_rp2_romleaf_rr/ck_rp4 228.1 qfd_tile_nk_rp2_romleaf_rr/ck_rp5 228.1 qfd_tile_nk_rp2_romleaf_rr/ck_rp6 228.1 qfd_tile_nk_rp2_romleaf_rr/ck_rp7 228.1 qfd_tile_nk_rp2_romleaf_rr/ck_rp8 228.1 qfd_tile_nk_rp2_romleaf_rr/ck_rp9 228.1 qfd_tile_nk_rp2_romleaf_rr/ck_rs 150.0 qfd_tile_nk_rp2_romleaf_rr/ck_rsw 150.0 qfd_tile_nk_rp2_romleaf_rr/ck_tx0 150.0 qfd_tile_nk_rp2_romleaf_rr/ck_tx1 150.0 qfd_tile_nk_rp2_romleaf_rr/ck_tx2 150.0 qfd_tile_nk_rp2_romleaf_rr/ck_tx3 202.0 qfd_tile_nk_rp2_romleaf_rr/ck_tx4 219.4 qfd_tile_nk_rp2_romleaf_rr/ck_tx5 214.1 qfd_tile_nk_rp2_romleaf_rr/ck_tx6 150.0 qfd_tile_nk_rp2_romleaf_rr/ck_tx7 150.0 qfd_tile_nl_rp2_romleaf_rr/ck 197.4 qfd_tile_nl_rp2_romleaf_rr/ck_de 150.0 qfd_tile_nl_rp2_romleaf_rr/ck_dw 150.0 qfd_tile_nl_rp2_romleaf_rr/ck_fa2 150.0 qfd_tile_nl_rp2_romleaf_rr/ck_fa4 150.0 qfd_tile_nl_rp2_romleaf_rr/ck_lsl0 176.7 qfd_tile_nl_rp2_romleaf_rr/ck_lsl1 176.7 qfd_tile_nl_rp2_romleaf_rr/ck_lsl2 176.7 qfd_tile_nl_rp2_romleaf_rr/ck_lsl3 176.7 qfd_tile_nl_rp2_romleaf_rr/ck_lsl4 176.7 qfd_tile_nl_rp2_romleaf_rr/ck_lsl5 176.7 qfd_tile_nl_rp2_romleaf_rr/ck_lsl6 176.7 qfd_tile_nl_rp2_romleaf_rr/ck_lsl7 176.7 qfd_tile_nl_rp2_romleaf_rr/ck_rn 150.0 qfd_tile_nl_rp2_romleaf_rr/ck_rnw 150.0 qfd_tile_nl_rp2_romleaf_rr/ck_rp0 228.1 qfd_tile_nl_rp2_romleaf_rr/ck_rp1 228.1 qfd_tile_nl_rp2_romleaf_rr/ck_rp2 228.1 qfd_tile_nl_rp2_romleaf_rr/ck_rp3 228.1 qfd_tile_nl_rp2_romleaf_rr/ck_rp4 228.1 qfd_tile_nl_rp2_romleaf_rr/ck_rp5 228.1 qfd_tile_nl_rp2_romleaf_rr/ck_rp6 228.1 qfd_tile_nl_rp2_romleaf_rr/ck_rp7 228.1 qfd_tile_nl_rp2_romleaf_rr/ck_rp8 228.1 qfd_tile_nl_rp2_romleaf_rr/ck_rp9 228.1 qfd_tile_nl_rp2_romleaf_rr/ck_rs 150.0 qfd_tile_nl_rp2_romleaf_rr/ck_rsw 150.0 qfd_tile_nl_rp2_romleaf_rr/ck_tx0 150.0 qfd_tile_nl_rp2_romleaf_rr/ck_tx1 150.0 qfd_tile_nl_rp2_romleaf_rr/ck_tx2 150.0 qfd_tile_nl_rp2_romleaf_rr/ck_tx3 202.0 qfd_tile_nl_rp2_romleaf_rr/ck_tx4 219.4 qfd_tile_nl_rp2_romleaf_rr/ck_tx5 208.3 qfd_tile_nl_rp2_romleaf_rr/ck_tx6 150.0 qfd_tile_nl_rp2_romleaf_rr/ck_tx7 150.0]
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
