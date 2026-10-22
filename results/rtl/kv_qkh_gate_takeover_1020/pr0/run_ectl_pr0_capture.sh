#!/bin/bash
set -eu
R=/srv/opentallas-scratch/claude/ref_gate/ot_qkh_ktree_lk_nc32c-20261020-041108/src
W=$PWD
S=$W/heads
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --version
for age in 13 14 15; do
  "$V" --binary --timing -j 2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD \
    -GHXK=$age --top-module tb_qkd_ectl3_pr0_capture -Mdir "$W/ectl_capture_$age" \
    "$W/tb_qkd_ectl3_pr0_capture.sv" "$S/qkd_ectl3_epoch_direct_s.sv" \
    "$S/qkd_ectl_a_tp8_epoch_direct.sv" "$S/qkd_ectl_native_direct_tp8.sv" \
    "$R/rtl/hdc/nearhbm/ot_qkd_ectl_parts.sv" "$R/rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_h.sv" \
    "$R/rtl/hdc/ot_hdc_delay.sv" "$R/rtl/lib/ot_rst_relay.sv" \
    "$W/ot_sram_1r1w_128x256_m1_r2c2.v" > "$W/ectl_capture_build_$age.log" 2>&1
  set +e
  "$W/ectl_capture_$age/Vtb_qkd_ectl3_pr0_capture" > "$W/ectl_capture_run_$age.log" 2>&1
  rc=$?
  set -e
  if [ "$age" = 13 ]; then
    test "$rc" = 0
    grep '^ECTL_SAFE32_CAPTURE_PASS' "$W/ectl_capture_run_$age.log"
  else
    test "$rc" -ne 0
    grep 'SCORE_AGE_MISMATCH' "$W/ectl_capture_run_$age.log"
  fi
done
