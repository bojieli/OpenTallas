#!/bin/bash
set -eu
R=/srv/opentallas-scratch/claude/ref_gate/ot_qkh_ktree_lk_nc32c-20261020-041108/src
W=$PWD
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --version
S=$W/heads
H=$R/rtl/hdc
set +e
"$V" --lint-only --timing -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN \
  -DKVD_HEADS=1 -DKVD_Q_FP32=1 -DSYNTHESIS --top-module tb_lk_wrapper_age -Mdir "$W/obj_wrong_param" \
  "$W/tb_lk_wrapper_age.sv" "$W/lane8_wrong_param_wrapper.v" "$W/lane8_core_renamed.v" \
  "$W/ot_qkh_head_native_r4_s_lk_nc32c.sv" "$S/ot_qkh_head_native_r4_s_lk.sv" \
  "$S/ot_qkh_head_native_r4.sv" "$S/ot_qkh_head_native_r4_ft.sv" "$S/ot_qkh_head_native.sv" \
  "$S/ot_qkh_head_native_r3.sv" "$S/qkh_head_gather_stage.sv" "$S/qkh_head_stages.sv" \
  "$H/nearhbm/ot_qkh_ktree_nc32c.sv" "$H/nearhbm/ot_qkh_ktree_lk.sv" "$H/nearhbm/ot_qkh_subtiles.sv" \
  "$H/nearhbm/ot_qwen_nearhbm_head_hs.sv" "$H/nearhbm/ot_qwen_nearhbm_prod.sv" \
  "$H/nearhbm/ot_qwen_nearhbm_attn_stack_h.sv" "$R/rtl/lib/ot_rst_relay.sv" \
  "$R/rtl/lib/ot_rst_relay_bounded32.sv" "$H/ot_hdc_delay.sv" "$H/ot_hdc_fp32_qkh_ncr.sv" \
  "$H/ot_hdc_fp32_mul_lat_ncr.sv" "$H/ot_hdc_fp32_add_lat_nr.sv" "$H/ot_hdc_fp32_add_lat.sv" \
  "$H/ot_hdc_fp32_mul_lat.sv" "$H/ot_hdc_prefix.sv" \
  "$R/physical/ref_tile/ot_qkh_ktree_m5/src/rtl/hdc/ot_hdc_fastfp.sv" > "$W/build_wrong_param.log" 2>&1
rc=$?
set -e
test "$rc" -ne 0
grep "ot_qkh_lane8_nc32c_requires7_12" "$W/build_wrong_param.log"
echo WRONG_PARAM_CONTROL_EXPECTED_FAIL
