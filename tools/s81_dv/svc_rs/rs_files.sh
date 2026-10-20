# S81U-SVC: source list of the dsdv_svc_rs slice (sourced by rs_bench.sh / rs_lint.sh)
#   score exchange = the S81U-SVCX split form (8 x dsdv_svc_sx_hrow head-parity half rows + closed dsfd_dvrly_276 relays);
#   SM share = ot_s81_su_sms with -DSU_SMU_T (hardened regional clusters dsfd_su_t_smhq x4 + dsfd_su_t_smhr)
D=rtl/dsrom_sys/s81_dv/svc_rs
SM=rtl/dsrom_sys/s81_dv/su_sm
RS_DEF=(-DSU_SMU_T)
RS_SRC=(rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv rtl/hdc/v41x/ot_hdc_v41x_attn_s.sv rtl/hdc/v41x/ot_hdc_v41x_kreg.sv
  rtl/hdc/v41x/ot_hdc_v41x_attn_tile_lat.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv rtl/hdc/v41x/ot_hdc_v41x_attn.sv
  rtl/hdc/v41x/ot_hdc_v41x_attn_staging.sv
  physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
  physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v
  rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_f12.sv
  rtl/hdc/v41x/ot_dsrom_su_add6.sv rtl/hdc/ot_hdc_delay.sv
  rtl/dsrom_sys/s81_ctrl/ot_s81_svc_job.sv rtl/dsrom_sys/s81_ph/svc/dsfd_svc_pc.sv
  rtl/dsrom_sys/s81_glue/ot_s81_rly.sv rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv276.sv
  $SM/ot_s81_su_sms.sv $SM/ot_s81_su_smq.sv $SM/ot_s81_su_smh.sv
  $SM/dsfd_su_t_smh.sv $SM/dsfd_su_t_smhq.sv $SM/dsfd_su_t_smhr.sv rtl/dsrom_sys/s81_suhc/hier/dsfd_su_t_sm.sv
  rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_sm.sv
  rtl/hdc/ot_hdc_fastfp_lat_f12.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_sfu.sv
  rtl/hdc/v41x/ot_dsrom_fp32_add_l6.sv rtl/hdc/v41x/ot_dsrom_su_f12.sv rtl/hdc/v41x/ot_dsrom_su_fdiv_f12.sv
  rtl/hdc/v41x/ot_dsrom_su_softmax_add6.sv rtl/hdc/v41x/ot_dsrom_su_softmax_add.sv rtl/hdc/v41x/ot_dsrom_su_softmax_f12r.sv
  rtl/hdc/v41x/ot_dsrom_su_softmax_m9.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv
  $D/dsdv_svc_sx_hrow.sv $D/dsdv_svc_sx.sv $D/dsdv_svc_att.sv $D/dsdv_svc_rs.sv
  rtl/hdc/v41x/ot_hdc_v41x_attn_hgrp_s81.sv $D/dsdv_svc_rs_glue.sv $D/attw/dsdv_svc_attw_f.sv $D/attw/lp/dsdv_svc_attw_f_lp.sv
  rtl/common/landed_parent/ot_pl_land.sv)   # SVC4: -DOT_SVC_ATTW_LP (landed attw) sources; unused otherwise
RS_LIB=(-v rtl/dsrom_sys/s81_ph/svc/dsfd_svc_c.sv)
