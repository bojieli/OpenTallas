# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ce_cts_roots {ck_h ck_c0 ck_c1 ck_c2 ck_c3 ck_c4 ck_c5 ck_c6 ck_c7 ck_c8 ck_c9}
set ::ot_ce_landed_cluster 1
set ::ot_ce_counts [dict create {ot_hbm_su_programme_pghead} 1 {ot_hbm_su_programme_pgcol_s} 7 {ot_hbm_su_programme_pgcol_l} 3]
source /src/physical/common_flow/clock_entries.tcl
set ::ot_cct_children [dict create {u_c0} {tt {278.1 314.2} ff {225.2 258.6} ss {364.8 404.1}} {u_c1} {tt {379.3 424.4} ff {308.4 348.3} ss {496.2 550}} {u_c2} {tt {379.3 424.4} ff {308.4 348.3} ss {496.2 550}} {u_c3} {tt {379.3 424.4} ff {308.4 348.3} ss {496.2 550}} {u_c4} {tt {278.1 314.2} ff {225.2 258.6} ss {364.8 404.1}} {u_c5} {tt {278.1 314.2} ff {225.2 258.6} ss {364.8 404.1}} {u_c6} {tt {278.1 314.2} ff {225.2 258.6} ss {364.8 404.1}} {u_c7} {tt {278.1 314.2} ff {225.2 258.6} ss {364.8 404.1}} {u_c8} {tt {278.1 314.2} ff {225.2 258.6} ss {364.8 404.1}} {u_c9} {tt {278.1 314.2} ff {225.2 258.6} ss {364.8 404.1}} {u_h} {tt {100.1 123.2} ff {80.9 104} ss {134.2 156.8}}]
source /src/physical/common_flow/child_centre_tap.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/hbm_su_pslice_c5_lp15b/clock_entry.sdc
}
