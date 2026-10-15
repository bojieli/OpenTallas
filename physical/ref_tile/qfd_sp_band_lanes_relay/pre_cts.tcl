# ref_tile PRE_CTS: io_ref boundary switch after the tree (qwen_die_masters/pre_cts_skew.tcl); clock entries: no tree, one port per child clock pin (sourced FIRST)
set ::ot_ce_cts_roots {ck ck_fn0 ck_fn1 ck_fn2 ck_fn3 ck_fn4 ck_fn5 ck_fn6 ck_fn7 ck_fe0 ck_fe1 ck_st0 ck_st1 ck_st2 ck_st3 ck_st4 ck_st5 ck_st6 ck_st7 ck_st8 ck_st9 ck_st10 ck_st11 ck_st12 ck_st13 ck_st14 ck_st15 ck_st16 ck_st17 ck_st18 ck_st19 ck_st20 ck_st21 ck_st22 ck_st23 ck_st24 ck_st25 ck_st26 ck_st27 ck_st28 ck_st29 ck_st30 ck_st31 ck_st32 ck_st33 ck_st34 ck_st35 ck_st36 ck_st37 ck_st38 ck_st39 ck_st40 ck_st41 ck_fq0 ck_fq1 ck_fq2 ck_fq3 ck_fj}
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/pre_cts_skew.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/qfd_sp_band_lanes_relay/clock_entry.sdc
}
