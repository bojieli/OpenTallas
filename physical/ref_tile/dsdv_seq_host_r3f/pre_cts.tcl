# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ckkm_ports {ck_lk 8 ck_sq 12 ck_vc 8}
source /src/physical/ref_tile/dsdv_seq_host_r3f/ckkm_multi.tcl
set ::ot_ce_cts_roots {ck_lk ck_sq ck_vc}
set ::ot_ce_landed_cluster 1
set ::ot_ce_counts [dict create {dsdv_sh_lk} 1 {dsdv_sh_sq} 1 {dsdv_sh_vc} 1]
source /src/physical/common_flow/clock_entries.tcl
set ::ot_cct_children [dict create {u_l0} {tt {512.9 598.3} ff {422.5 491.4} ss {659.6 773.3}} {u_l1} {tt {239.1 293.4} ff {195.9 247.9} ss {309.9 367.6}} {u_l2} {tt {285.9 316.8} ff {230.3 259.9} ss {379.3 412.9}}]
source /src/physical/common_flow/child_centre_tap.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/dsdv_seq_host_r3f/clock_entry.sdc
}
