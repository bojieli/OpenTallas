# ref_tile PRE_CTS: io_ref boundary switch after the tree (qwen_die_masters/pre_cts_skew.tcl); clock entries: no tree, one port per child clock pin (sourced FIRST)
set ::ot_ce_cts_roots {ck ck_rn ck_rs ck_rsw ck_rnw ck_dw ck_de ck_tx0 ck_tx1 ck_tx2 ck_tx3 ck_tx4 ck_tx5 ck_tx6 ck_tx7 ck_fa2 ck_fa4}
source /src/physical/common_flow/clock_entries.tcl
source /src/tools/qwen_romleaf/rc14_2000/baseline/ck_km_split.tcl
source /src/tools/qwen_romleaf/rc14_2000/baseline/ck_km_cts_nets.tcl
source /src/physical/qwen_die_masters/pre_cts_skew.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/qfd_tile_nl_romleaf_rpf/clock_entry.sdc
}
