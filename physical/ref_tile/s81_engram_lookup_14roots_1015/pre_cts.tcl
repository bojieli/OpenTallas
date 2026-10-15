# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ce_cts_roots {ck ck_hash[0] ck_hash[1] ck_hash[2] ck_hash[3] ck_hash[4] ck_hash[5] ck_rows[0] ck_rows[1] ck_rows[2] ck_rows[3] ck_rows[4] ck_rows[5] ck_seed}
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/s81_engram_lookup_14roots_1015/clock_entry.sdc
}
