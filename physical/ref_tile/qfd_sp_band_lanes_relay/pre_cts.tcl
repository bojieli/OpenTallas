# ref_tile PRE_CTS: io_ref boundary switch after the tree (qwen_die_masters/pre_cts_skew.tcl); clock entries: no tree, one port per child clock pin (sourced FIRST)
set ::ot_ce_cts_roots {ck ck_fn[0] ck_fn[1] ck_fn[2] ck_fn[3] ck_fn[4] ck_fn[5] ck_fn[6] ck_fn[7] ck_fe0 ck_fe1 ck_st[0] ck_st[1] ck_st[2] ck_st[3] ck_st[4] ck_st[5] ck_st[6] ck_st[7] ck_st[8] ck_st[9] ck_st[10] ck_st[11] ck_st[12] ck_st[13] ck_st[14] ck_st[15] ck_st[16] ck_st[17] ck_st[18] ck_st[19] ck_st[20] ck_st[21] ck_st[22] ck_st[23] ck_st[24] ck_st[25] ck_st[26] ck_st[27] ck_st[28] ck_st[29] ck_st[30] ck_st[31] ck_st[32] ck_st[33] ck_st[34] ck_st[35] ck_st[36] ck_st[37] ck_st[38] ck_st[39] ck_st[40] ck_st[41] ck_fq[0] ck_fq[1] ck_fq[2] ck_fq[3] ck_fj}
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/pre_cts_skew.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/qfd_sp_band_lanes_relay/clock_entry.sdc
}
