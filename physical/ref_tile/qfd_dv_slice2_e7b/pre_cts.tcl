# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ce_cts_roots {ck_r_fw ck_r_fe ck_r_st0 ck_r_st1 ck_r_st2 ck_r_st3 ck_r_st4 ck_r_st5 ck_r_st6 ck_r_st7 ck_r_stm ck_r_ctl ck_r_sc ck_r_su ck_r_tap ck_r_hc0 ck_r_hc1 ck_r_hc2 ck_r_hc3}
set ::ot_ce_landed_cluster 1
set ::ot_ce_counts [dict create {qfd_dv_redstn2_region} 8 {ot_hdc_sfu_rsq_t} 8 {ot_hdc_sfu_exp_t} 8 {ot_hdc_sfu_rcp_t} 8 {qfd_dv_lane_h_safe2} 8 {qfd_dv_s5_lrly} 8 {qfd_dv_s5_ctl_repair4_leaf} 1 {qfd_dv_stream_tile} 1 {qfd_dv_slice_tload} 1 {qfd_dv_s5_btab_s4} 1 {qfd_dv_s5_su8_rst3} 1 {qfd_dv_s8x_vmr} 3 {qfd_dv_s8x_prog} 1 {qfd_dv_s8x_crh} 2 {qfd_dv_s8x_btab} 1]
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/qfd_dv_slice2_e7b/clock_entry.sdc
}
