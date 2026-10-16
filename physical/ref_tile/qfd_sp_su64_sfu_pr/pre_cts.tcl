# ref_tile PRE_CTS: io_ref boundary switch after the tree (qwen_die_masters/pre_cts_skew.tcl); clock entries: no tree, one port per child clock pin (sourced FIRST)
set ::ot_ce_cts_roots {ck ck_lane0 ck_lane1 ck_lane2 ck_lane3 ck_lane4 ck_lane5 ck_lane6 ck_lane7 ck_lane8 ck_lane9 ck_lane10 ck_lane11 ck_lane12 ck_lane13 ck_lane14 ck_lane15 ck_lane16 ck_lane17 ck_lane18 ck_lane19 ck_lane20 ck_lane21 ck_lane22 ck_lane23 ck_lane24 ck_lane25 ck_lane26 ck_lane27 ck_lane28 ck_lane29 ck_lane30 ck_lane31 ck_lane32 ck_lane33 ck_lane34 ck_lane35 ck_lane36 ck_lane37 ck_lane38 ck_lane39 ck_lane40 ck_lane41 ck_lane42 ck_lane43 ck_lane44 ck_lane45 ck_lane46 ck_lane47 ck_lane48 ck_lane49 ck_lane50 ck_lane51 ck_lane52 ck_lane53 ck_lane54 ck_lane55 ck_lane56 ck_lane57 ck_lane58 ck_lane59 ck_lane60 ck_lane61 ck_lane62 ck_lane63 ck_align0 ck_align1 ck_align2 ck_align3 ck_align4 ck_align5 ck_align6 ck_align7 ck_align8 ck_align9 ck_align10 ck_align11 ck_align12 ck_align13 ck_align14 ck_align15 ck_red0 ck_red1 ck_red2 ck_red3 ck_red4 ck_red5 ck_red6 ck_red7 ck_red8}
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/pre_cts_skew.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/qfd_sp_su64_sfu_pr/clock_entry.sdc
}
