#!/bin/bash
# RTL-BUILD-KV/ASTK 2026-10-18: lockstep of the heads without nb_d (ot_qkh_head_native_r4_s / _ft_s) against
# ot_qkh_head_native_r4 / _ft.  usage: head_st_bench.sh OUTDIR [MUT]   MUT 0: PASS; MUT 1 (new heads MUT 1): FAIL
set -e
R=$(cd "$(dirname "$0")/../.." && pwd); OUT=$1; MUT=${2:-0}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
[ -x "$V" ] || V=$(command -v verilator)
mkdir -p "$OUT"
S=$R/rtl/qwen_sys/split_20261014; H=$R/rtl/hdc
python3 "$R/tools/qwen_kv_die/head_st_rtl.py" --check || { echo "FAIL qkh_head_r4_s generated RTL stale"; exit 1; }
SRC="$R/rtl/test/qwen_kv_die/tb_qkh_head_r4_s.sv $S/ot_qkh_head_native_r4_s.sv $S/ot_qkh_head_native_r4.sv $S/ot_qkh_head_native_r4_ft.sv
 $S/ot_qkh_head_native.sv $S/ot_qkh_head_native_r3.sv $S/qkh_head_gather_stage.sv $S/qkh_head_stages.sv
 $H/nearhbm/ot_qkh_subtiles.sv $H/nearhbm/ot_qwen_nearhbm_head_hs.sv $H/nearhbm/ot_qwen_nearhbm_prod.sv
 $H/nearhbm/ot_qwen_nearhbm_attn_stack_h.sv $R/rtl/lib/ot_rst_relay.sv $H/ot_hdc_delay.sv $H/ot_hdc_fp32_add_lat_nr.sv
 $H/ot_hdc_fp32_add_lat.sv $H/ot_hdc_fp32_mul_lat.sv $H/ot_hdc_prefix.sv $H/ot_hdc_fastfp.sv"
"$V" --binary -j 16 --timing -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_qkh_head_r4_s -DKVD_HEADS=1 \
  -DKVD_Q_FP32=1 -DKVD_HSTMUT=$MUT -Mdir "$OUT/obj" -o Vtb $SRC > "$OUT/build.log" 2>&1 || { tail -30 "$OUT/build.log"; echo "FAIL qkh_head_r4_s build"; exit 1; }
"$OUT/obj/Vtb" > "$OUT/run.log" 2>&1 || true
grep -E '^(PASS|FAIL|MISMATCH)' "$OUT/run.log" | head -12
grep -q '^PASS qkh_head_r4_s' "$OUT/run.log"
