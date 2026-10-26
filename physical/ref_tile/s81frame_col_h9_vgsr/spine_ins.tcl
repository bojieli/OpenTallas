# ref_tile cluster clock: the pre-placed balanced clock SPINE (physical/common_flow/clock_spine.tcl, el1011-hbm-attn
# c11a6e02a: attention halves leaf spread 1,634 -> 24 ps; idx w8 cluster 518 ps skew) replaces TritonCTS for the cluster
# clock.  Leaf target = arrival at the sink pin PLUS the hard child's own clock insertion (its TT lib max_clock_tree_path),
# so the spine balances the flops INSIDE the children against the cluster's own flops (CLOCK LATENCY ACROSS THE HIERARCHY).
set ::ot_ref_child_ins [dict create dsfd_bf_front_roots/ck 214.8 dsfd_bf_front_roots/io_clk 145.4 dsfd_bf_front_roots/io_e 132.7 dsfd_bf_front_roots/io_n 137.0 dsfd_bf_front_roots/io_w 121.6 dsfd_cfifo_crs4/cr 176.6 dsfd_cfifo_crs4/cr_s 53.3 {dsfd_cfifo_crs4/xk[0]} 119.6 {dsfd_cfifo_crs4/xk[1]} 100.9 {dsfd_cfifo_crs4/xk[2]} 118.6 {dsfd_cfifo_crs4/xk[3]} 103.2 dsfd_dvrly_276_NS/ck 106.6 {dsfd_node_LLd/clk[0]} 104.6 {dsfd_node_LLfd/clk[0]} 106.5 {dsfd_node_LLfu/clk[0]} 109.7 {dsfd_node_NNfd/clk[0]} 110.5 {dsfd_node_NNfu/clk[0]} 112.0 {dsfd_qbank_N/ck[0]} 76.8 {dsfd_qbank_S/ck[0]} 92.1 {dsfd_rstg/ck[0]} 54.2 {ot_s81_cfg7_seq/clk[0]} 87.1 {ot_s81_cfg7_seq_bfp/clk[0]} 93.2 ot_s81_sstn_base566/ck 90.7 ot_s81_sstn_payload536/ck 88.0 ot_v41_bf_col/clk 544.0 ot_v41_rom_elem_q_qxpq_w10/clk 510.3]
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
