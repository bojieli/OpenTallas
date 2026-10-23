# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ce_cts_roots {ck_u ck_upn ck_upne ck_c ck_m ck_cpw ck_cpe ck_xs ck_mpse}
set ::ot_ce_landed_cluster 1
set ::ot_ce_counts [dict create {ot_hbm_sm_pv_merge_s3} 1 {ot_hbm_accel_smh_tct} 1 {ot_hbm_accel_smh_bdc} 1 {ot_hbm_accel_smh_tcl_gu} 2 {ot_hbm_accel_smh_xs} 1 {ot_smh_tr_group_row_w} 1 {ot_smh_tr_group_row_e} 1]
source /src/physical/common_flow/clock_entries.tcl
set ::ot_cct_children [dict create {u_bdc1} {tt {172 188.1} ff {139.7 154.9} ss {227 244.2}} {u_h01} {tt {168.8 181.1} ff {136.7 148.7} ss {223.3 236.2}} {u_h11} {tt {168.8 181.1} ff {136.7 148.7} ss {223.3 236.2}} {u_mg1.u_merge} {tt {263.2 313.2} ff {215.4 262.4} ss {342.3 397}} {u_qk1} {tt {170.4 183.5} ff {137.8 151.1} ss {225.1 238.8}} {u_row1} {tt {132.8 171.7} ff {107.1 143.5} ss {177.3 220.8}} {u_rowe1} {tt {104.3 118.7} ff {85.2 100} ss {137.4 151.8}} {u_xs1} {tt {453.5 528.9} ff {366.8 425.7} ss {597.3 700.9}}]
source /src/physical/common_flow/child_centre_tap.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/smh_rp8s_m/clock_entry.sdc
}
