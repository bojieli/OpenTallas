#!/bin/bash
# KVE-2-ASTK 2026-10-17: lockstep bench of the credit-free, lane-free static ASTK strip (qkd_astk_strip_st) against the
# selected static composition qkd_astk_native_stack_cal.  usage: astk_static_bench.sh OUTDIR [MUT]
#   MUT 0: expect "PASS qkd_astk_strip_st lockstep";  MUT 1 (ep_s) / 2 (ex_s) / 3 (ctl_s): expect "FAIL qkd_astk_strip_st"
set -e
R=$(cd "$(dirname "$0")/../.." && pwd); OUT=$1; MUT=${2:-0}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
[ -x "$V" ] || V=$(command -v verilator)
mkdir -p "$OUT"
M=$R/physical/qkd_astk_strip/macros
SRC="$R/rtl/test/qwen_kv_die/tb_qkd_astk_strip_st.sv $R/rtl/qwen_sys/split_20261014/qkd_astk_strip_st.sv
 $R/rtl/qwen_sys/split_20261014/qkd_astk_static_leaves.sv $R/rtl/qwen_sys/kv_die_20261009/qkd_astk_leaves.sv
 $R/rtl/qwen_sys/split_20261014/qkd_astk_cal_gen.sv $R/rtl/qwen_sys/split_20261014/qkd_astk_native_er_service.sv
 $R/rtl/qwen_sys/split_20261014/qkd_astk_phys.sv $R/rtl/hdc/ot_hdc_delay.sv $R/rtl/hdc/ot_hdc_fp32_add_lat.sv $R/rtl/hdc/ot_hdc_fp32_add_lat_nr.sv
 $R/rtl/hdc/nearhbm/ot_qwen_nearhbm_sfu_p.sv $R/rtl/hdc/ot_hdc_sfu.sv $R/rtl/hdc/ot_hdc_prefix.sv $R/rtl/hdc/ot_hdc_fastfp.sv
 $R/rtl/hdc/ot_hdc_fp32_mul_lat.sv $M/ot_sram_1r1w_256x128_m1_r2c2/ot_sram_1r1w_256x128_m1_r2c2.v
 $M/ot_sram_1r1w_64x128_m1_r2c2/ot_sram_1r1w_64x128_m1_r2c2.v"
"$V" --binary -j 16 --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_qkd_astk_strip_st -DKVD_HEADS=1 -DKVD_STMUT=$MUT \
  -Mdir "$OUT/obj" -o Vtb $SRC > "$OUT/build.log" 2>&1 || { tail -30 "$OUT/build.log"; echo "FAIL qkd_astk_strip_st build"; exit 1; }
"$OUT/obj/Vtb" > "$OUT/run.log" 2>&1 || true
grep -E '^(PASS|FAIL|MISMATCH)' "$OUT/run.log" | head -12
grep -q '^PASS qkd_astk_strip_st' "$OUT/run.log"
