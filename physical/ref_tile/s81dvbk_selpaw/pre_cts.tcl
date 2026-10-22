# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ce_cts_roots {ck_core ck_r1 ck_r2 ck_r3 ck_r4 ck_r5 ck_r6 ck_r7 ck_r8 ck_r9 ck_r10 ck_r11 ck_r12 ck_r13 ck_r14 ck_r15 ck_r16 ck_r17 ck_r18 ck_r19 ck_r20 ck_r21 ck_r22 ck_r23 ck_r24 ck_r25 ck_r26 ck_r27 ck_r28 ck_r29 ck_r30 ck_r31 ck_r32 ck_r33 ck_r34 ck_r35 ck_r36 ck_r37 ck_r38}
set ::ot_ce_landed_cluster 1
set ::ot_ce_counts [dict create {dsdv_bk_g} 1 {dsdv_bksel_q} 4 {dsfd_dvrly_276_SN} 1 {dsfd_dvrly_276_NS} 1]
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/s81dvbk_selpaw/clock_entry.sdc
}
