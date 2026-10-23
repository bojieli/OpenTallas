# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ce_cts_roots {ck_lk ck_sq ck_vc}
set ::ot_ce_landed_cluster 1
set ::ot_ce_counts [dict create {dsdv_sh_lk} 1 {dsdv_sh_sq} 1 {dsdv_sh_vc} 1 {dsdv_sh_lb_lk} 1 {dsdv_sh_lb_vc} 1]
source /src/physical/common_flow/clock_entries.tcl
set ::ot_cct_children [dict create {u_blk} {tt {253.8 292} ff {206.4 243.4} ss {331.5 372.4}} {u_bvc} {tt {256.5 304.2} ff {207.3 253.5} ss {338.1 389.1}} {u_l0} {tt {512.9 598.3} ff {422.5 491.4} ss {659.6 773.3}} {u_l1} {tt {239.1 293.4} ff {195.9 247.9} ss {309.9 367.6}} {u_l2} {tt {285.9 316.8} ff {230.3 259.9} ss {379.3 412.9}}]
source /src/physical/common_flow/child_centre_tap.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/dsdv_seq_host_b1f2/clock_entry.sdc
}
