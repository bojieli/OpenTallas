# Generated from exact hashed native Lib contracts; four explicit S81 ROMs only.
# INVBUF sha256 8d6db2c2f83c3c162be54a5e102b2d379fcaaaef2db5f0b1d4152c395d01fea1
# SEQ sha256 57a0b403485b99ebd676942af4673ac086b86c7c75fbdc3e5c0038501dd22ba3
proc ot_s81_cf_rom_provider_contract {tap_net tap_parity} {
  set c [dict create]
  dict set c provider {u_bound.u_u_r0_u_cf}
  dict set c provider_master {dsfd_cfifo_crs4}
  dict set c provider_pin {rs}
  dict set c provider_clock {cr}
  dict set c source_clock_net {clk}
  dict set c sink_master {ot_v41_rom_elem_q_qxpq_w10_gb}
  dict set c sink_pin {rst_n}
  dict set c sink_clock {clk}
  dict set c tap_key {rst_n_t27}
  dict set c libraries {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz} {8d6db2c2f83c3c162be54a5e102b2d379fcaaaef2db5f0b1d4152c395d01fea1}
  dict set c libraries {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib} {57a0b403485b99ebd676942af4673ac086b86c7c75fbdc3e5c0038501dd22ba3}
  dict set c tap_net $tap_net
  dict set c tap_parity $tap_parity
  dict set c stages [list {u_bound.u_d2_u_r0_u_cf_rs.r[0]$_DFF_P_} {u_bound.u_d2_u_r0_u_cf_rs.q$_DFF_P_} {u_bound.u_d15_u_r0_u_cf_rs.r[2]$_DFF_P_} {u_bound.u_d15_u_r0_u_cf_rs.r[3]$_DFF_P_} {u_bound.u_d15_u_r0_u_cf_rs.r[4]$_DFF_P_} {u_bound.u_d15_u_r0_u_cf_rs.r[5]$_DFF_P_} {u_bound.u_d15_u_r0_u_cf_rs.r[6]$_DFF_P_} {u_bound.u_d15_u_r0_u_cf_rs.r[7]$_DFF_P_} {u_bound.u_d15_u_r0_u_cf_rs.r[8]$_DFF_P_} {u_bound.u_d15_u_r0_u_cf_rs.r[9]$_DFF_P_} {u_bound.u_d15_u_r0_u_cf_rs.r[10]$_DFF_P_} {u_bound.u_d15_u_r0_u_cf_rs.r[11]$_DFF_P_} {u_bound.u_d15_u_r0_u_cf_rs.r[12]$_DFF_P_} {u_bound.u_d15_u_r0_u_cf_rs.r[13]$_DFF_P_} {u_bound.u_d15_u_r0_u_cf_rs.q$_DFF_P_}]
  dict set c sinks [list {u_bound.u_u_r0_u_e0} {u_bound.u_u_r0_u_e2} {u_bound.u_u_r0_u_e3} {u_bound.u_u_r0_u_e4}]
  dict set c buffers {BUFx10_ASAP7_75t_R} [dict create input {A} output {Y} inverted {0}]
  dict set c buffers {BUFx12_ASAP7_75t_R} [dict create input {A} output {Y} inverted {0}]
  dict set c buffers {BUFx12f_ASAP7_75t_R} [dict create input {A} output {Y} inverted {0}]
  dict set c buffers {BUFx16f_ASAP7_75t_R} [dict create input {A} output {Y} inverted {0}]
  dict set c buffers {BUFx24_ASAP7_75t_R} [dict create input {A} output {Y} inverted {0}]
  dict set c buffers {BUFx2_ASAP7_75t_R} [dict create input {A} output {Y} inverted {0}]
  dict set c buffers {BUFx3_ASAP7_75t_R} [dict create input {A} output {Y} inverted {0}]
  dict set c buffers {BUFx4_ASAP7_75t_R} [dict create input {A} output {Y} inverted {0}]
  dict set c buffers {BUFx4f_ASAP7_75t_R} [dict create input {A} output {Y} inverted {0}]
  dict set c buffers {BUFx5_ASAP7_75t_R} [dict create input {A} output {Y} inverted {0}]
  dict set c buffers {BUFx6f_ASAP7_75t_R} [dict create input {A} output {Y} inverted {0}]
  dict set c buffers {BUFx8_ASAP7_75t_R} [dict create input {A} output {Y} inverted {0}]
  dict set c buffers {CKINVDCx10_ASAP7_75t_R} [dict create input {A} output {Y} inverted {1}]
  dict set c buffers {CKINVDCx11_ASAP7_75t_R} [dict create input {A} output {Y} inverted {1}]
  dict set c buffers {CKINVDCx12_ASAP7_75t_R} [dict create input {A} output {Y} inverted {1}]
  dict set c buffers {CKINVDCx14_ASAP7_75t_R} [dict create input {A} output {Y} inverted {1}]
  dict set c buffers {CKINVDCx16_ASAP7_75t_R} [dict create input {A} output {Y} inverted {1}]
  dict set c buffers {CKINVDCx20_ASAP7_75t_R} [dict create input {A} output {Y} inverted {1}]
  dict set c buffers {CKINVDCx5p33_ASAP7_75t_R} [dict create input {A} output {Y} inverted {1}]
  dict set c buffers {CKINVDCx6p67_ASAP7_75t_R} [dict create input {A} output {Y} inverted {1}]
  dict set c buffers {CKINVDCx8_ASAP7_75t_R} [dict create input {A} output {Y} inverted {1}]
  dict set c buffers {CKINVDCx9p33_ASAP7_75t_R} [dict create input {A} output {Y} inverted {1}]
  dict set c buffers {HB1xp67_ASAP7_75t_R} [dict create input {A} output {Y} inverted {0}]
  dict set c buffers {HB2xp67_ASAP7_75t_R} [dict create input {A} output {Y} inverted {0}]
  dict set c buffers {HB3xp67_ASAP7_75t_R} [dict create input {A} output {Y} inverted {0}]
  dict set c buffers {HB4xp67_ASAP7_75t_R} [dict create input {A} output {Y} inverted {0}]
  dict set c buffers {INVx11_ASAP7_75t_R} [dict create input {A} output {Y} inverted {1}]
  dict set c buffers {INVx13_ASAP7_75t_R} [dict create input {A} output {Y} inverted {1}]
  dict set c buffers {INVx1_ASAP7_75t_R} [dict create input {A} output {Y} inverted {1}]
  dict set c buffers {INVx2_ASAP7_75t_R} [dict create input {A} output {Y} inverted {1}]
  dict set c buffers {INVx3_ASAP7_75t_R} [dict create input {A} output {Y} inverted {1}]
  dict set c buffers {INVx4_ASAP7_75t_R} [dict create input {A} output {Y} inverted {1}]
  dict set c buffers {INVx5_ASAP7_75t_R} [dict create input {A} output {Y} inverted {1}]
  dict set c buffers {INVx6_ASAP7_75t_R} [dict create input {A} output {Y} inverted {1}]
  dict set c buffers {INVx8_ASAP7_75t_R} [dict create input {A} output {Y} inverted {1}]
  dict set c buffers {INVxp33_ASAP7_75t_R} [dict create input {A} output {Y} inverted {1}]
  dict set c buffers {INVxp67_ASAP7_75t_R} [dict create input {A} output {Y} inverted {1}]
  dict set c flop [dict create master {DFFHQNx1_ASAP7_75t_R} output {QN} data {D} clock {CLK} inverted {1}]
  return $c
}
