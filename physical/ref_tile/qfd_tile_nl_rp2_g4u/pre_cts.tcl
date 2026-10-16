# ref_tile PRE_CTS: io_ref boundary switch after the tree (qwen_die_masters/pre_cts_skew.tcl); clock entries: no tree, one port per child clock pin (sourced FIRST)
set ::ot_ce_cts_roots {ck ck_rn ck_rs ck_rp3 ck_rp8 ck_rp4 ck_rp9 ck_rp0 ck_rp2 ck_rp5 ck_rp1 ck_rp7 ck_rp6 ck_fa2 ck_fa4}
set ::ot_ce_soft_root_macros {ot_rom_4096x266_m8}
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/pre_cts_skew.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/qfd_tile_nl_rp2_g4u/clock_entry.sdc
}
