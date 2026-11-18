#!/bin/bash
# KV-KT-E0 2026-11-18: control tile + four native heads, kt stations KT_ST 2 with HXK + 2 against today (see the bench header).
# usage: head_kst_ectl_bench.sh OUTDIR      (run inside an admitted ot-run unit; one build: 5 tiles, 5 heads; ~700 C++ files:
#   ot-heavy caps the compile jobs at MEM / 30 GB, so ask for the memory of the jobs you want, e.g. --mem 240 = -j8)
set -u
R=$(cd "$(dirname "$0")/../.." && pwd); OUT=$(mkdir -p "$1" && cd "$1" && pwd)
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
[ -x "$V" ] || V=$(command -v verilator)
J=${KST_JOBS:-32}
S=$R/rtl/qwen_sys/split_20261014; H=$R/rtl/hdc
python3 -I "$R/tools/qwen_kv_die/head_st_rtl.py" --check || { echo "FAIL qkh_head_kst generated RTL stale"; exit 1; }
SRC="$R/rtl/test/qwen_kv_die/tb_qkh_kst_ectl.sv $S/qkd_ectl3_epoch_direct_s.sv $S/qkd_ectl_a_tp8_epoch_direct.sv $S/qkd_ectl_native_direct_tp8.sv
 $H/nearhbm/ot_qkd_ectl_parts.sv $R/physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
 $S/ot_qkh_head_native_r4_kst.sv $S/ot_qkh_head_kst.sv $S/ot_qkh_head_native_r4_s_lk.sv $S/ot_qkh_head_native_r4.sv
 $S/ot_qkh_head_native.sv $S/ot_qkh_head_native_r3.sv
 $H/nearhbm/ot_qkh_subtiles.sv $H/nearhbm/ot_qkh_ktree_lk.sv $H/nearhbm/ot_qwen_nearhbm_head_hs.sv $H/nearhbm/ot_qwen_nearhbm_prod.sv
 $H/nearhbm/ot_qwen_nearhbm_attn_stack_h.sv $R/rtl/lib/ot_rst_relay.sv $H/ot_hdc_delay.sv $H/ot_hdc_fp32_add_lat_nr.sv
 $H/ot_hdc_fp32_add_lat.sv $H/ot_hdc_fp32_mul_lat.sv $H/ot_hdc_prefix.sv $H/ot_hdc_fastfp.sv"
: > "$OUT/result.txt"; fail=0; npass=0
"$V" --binary -j $J --timing -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTH --top-module tb_qkh_kst_ectl -DKVD_HEADS=1 -DKVD_Q_FP32=1 \
  -O1 -CFLAGS -O0 -Mdir "$OUT/obj" -o Vtb $SRC > "$OUT/build.log" 2>&1 || { tail -30 "$OUT/build.log"; echo "FAIL build" | tee -a "$OUT/result.txt"; exit 1; }
for hid in 0 1 2 3; do for seed in 7 19; do
  "$OUT/obj/Vtb" +SEED=$seed +HID=$hid > "$OUT/run_h${hid}_s$seed.log" 2>&1 || true
  line=$(grep -E '^(PASS|FAIL) qkh_kst_ectl' "$OUT/run_h${hid}_s$seed.log" | head -1)
  if [ "${line%% *}" = PASS ]; then npass=$((npass+1)); else fail=1; fi
  echo "h$hid s$seed: ${line:-no result line}" >> "$OUT/result.txt"; grep -E '^(FIELD|INFO)' "$OUT/run_h${hid}_s$seed.log" | sed 's/^/    /' >> "$OUT/result.txt"
done; done
if [ $fail = 0 ] && [ $npass = 8 ]; then echo "PASS qkh_kst_ectl: $npass runs (4 head ids x 2 seeds), negative controls (no HXK move; 14-lane form) off the law in every run" | tee -a "$OUT/result.txt"
else echo "FAIL qkh_kst_ectl: pass $npass fail $fail" | tee -a "$OUT/result.txt"; exit 1; fi
