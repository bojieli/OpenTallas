#!/bin/bash
set -eu
R=/srv/opentallas-scratch/claude/ref_gate/ot_qkh_ktree_lk_nc32c-20261020-041108/src
W=$PWD
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --version
python3 - "$R" "$W" <<'PY'
from pathlib import Path
import sys,hashlib,json
r,w=map(Path,sys.argv[1:]);p=r/'rtl/hdc/nearhbm/ot_qkh_lane8_nc32c.sv';t=p.read_text()
assert t.count('module ot_qkh_lane8_nc32c #(')==1
(w/'lane8_core_renamed.v').write_text(t.replace('module ot_qkh_lane8_nc32c #(', 'module ot_qkh_lane8_nc32c__ot_pr_core #(',1))
(w/'source_identity.json').write_text(json.dumps({'base_source':str(r),'core_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'wrapper_sha256':hashlib.sha256((w/'lane8_actual_pin_wrapper.v').read_bytes()).hexdigest(),'head_sources':{x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted((w/'heads').glob('*.sv'))},'rename':'sole core module identifier; actual shipped wrapper unmodified','scope':'private complete LK RTL measurement; no CLOSED/native receipt'},indent=2)+'\n')
PY
S=$W/heads
H=$R/rtl/hdc
"$V" --binary --timing -j 8 -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN \
  -DKVD_HEADS=1 -DKVD_Q_FP32=1 -DSYNTHESIS --top-module tb_lk_wrapper_age -Mdir "$W/obj" \
  "$W/tb_lk_wrapper_age.sv" "$W/lane8_actual_pin_wrapper.v" "$W/lane8_core_renamed.v" \
  "$W/ot_qkh_head_native_r4_s_lk_nc32c.sv" "$S/ot_qkh_head_native_r4_s_lk.sv" \
  "$S/ot_qkh_head_native_r4.sv" "$S/ot_qkh_head_native_r4_ft.sv" "$S/ot_qkh_head_native.sv" \
  "$S/ot_qkh_head_native_r3.sv" "$S/qkh_head_gather_stage.sv" "$S/qkh_head_stages.sv" \
  "$H/nearhbm/ot_qkh_ktree_nc32c.sv" "$H/nearhbm/ot_qkh_ktree_lk.sv" "$H/nearhbm/ot_qkh_subtiles.sv" \
  "$H/nearhbm/ot_qwen_nearhbm_head_hs.sv" "$H/nearhbm/ot_qwen_nearhbm_prod.sv" \
  "$H/nearhbm/ot_qwen_nearhbm_attn_stack_h.sv" "$R/rtl/lib/ot_rst_relay.sv" \
  "$R/rtl/lib/ot_rst_relay_bounded32.sv" "$H/ot_hdc_delay.sv" "$H/ot_hdc_fp32_qkh_ncr.sv" \
  "$H/ot_hdc_fp32_mul_lat_ncr.sv" "$H/ot_hdc_fp32_add_lat_nr.sv" "$H/ot_hdc_fp32_add_lat.sv" \
  "$H/ot_hdc_fp32_mul_lat.sv" "$H/ot_hdc_prefix.sv" \
  "$R/physical/ref_tile/ot_qkh_ktree_m5/src/rtl/hdc/ot_hdc_fastfp.sv" > "$W/build.log" 2>&1
for seed in 11 19; do
  "$W/obj/Vtb_lk_wrapper_age" +seed=$seed > "$W/seed${seed}.log" 2>&1
  grep -E '^LK_AGE' "$W/seed${seed}.log"
  grep -q '^LK_AGE_PASS' "$W/seed${seed}.log"
done
# Compiler wrong-age causal controls use the identical real RTL binary.
for age in 0 1; do
  "$W/obj/Vtb_lk_wrapper_age" +seed=11 +expect_lag=$age > "$W/wrong_age${age}.log" 2>&1
  grep '^LK_AGE_FAIL' "$W/wrong_age${age}.log"
done
