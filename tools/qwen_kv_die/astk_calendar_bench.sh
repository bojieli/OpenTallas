#!/bin/bash
# HKV-ASTK 2026-10-18: production-profile calendar bench of the actual ASTK strip with inline e-read (qkd_astk_strip_er_st).
# usage: astk_calendar_bench.sh OUTDIR [MUT] [STRIDE] [RL] [DER] [-- +T=.. +LMAX=.. +EXP=.. +Z=.. +READ=..]
#   MUT 0 expect "PASS qkd_astk_calendar"; MUT 1 ep_s / 2 ex_s / 3 ctl_s expect "FAIL qkd_astk_calendar".
#   STRIDE = ctl Z stride (closed ctl_s: 4), RL = chain hop edges, DER 0 = star er_tap_st ERL3, 1 = distributed owner chain.
#   The binary is reused when OUTDIR/obj/Vtb exists (sweeps: astk_calendar_sweep.sh).
set -e
R=$(cd "$(dirname "$0")/../.." && pwd); OUT=$1; MUT=${2:-0}; STRIDE=${3:-4}; RL=${4:-3}; DER=${5:-1}
shift $(( $# < 5 ? $# : 5 )); [ "${1:-}" = "--" ] && shift
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
[ -x "$V" ] || V=$(command -v verilator)
mkdir -p "$OUT"
M=$R/physical/qkd_astk_strip/macros
S=$R/rtl/qwen_sys/split_20261014
SRC="$R/rtl/test/qwen_kv_die/tb_qkd_astk_calendar.sv $S/qkd_astk_strip_er_st.sv $S/qkd_astk_er_tap_st.sv $S/qkd_astk_er_chain_st.sv
 $S/qkd_astk_er_owner_st.sv $S/qkd_astk_strip_st.sv $S/qkd_astk_static_leaves.sv $R/rtl/qwen_sys/kv_die_20261009/qkd_astk_leaves.sv
 $S/qkd_astk_phys.sv $R/rtl/hdc/ot_hdc_delay.sv $R/rtl/hdc/ot_hdc_fp32_add_lat.sv $R/rtl/hdc/ot_hdc_fp32_add_lat_nr.sv
 $R/rtl/hdc/nearhbm/ot_qwen_nearhbm_sfu_p.sv $R/rtl/hdc/ot_hdc_sfu.sv $R/rtl/hdc/ot_hdc_prefix.sv $R/rtl/hdc/ot_hdc_fastfp.sv
 $R/rtl/hdc/ot_hdc_fp32_mul_lat.sv $M/ot_sram_1r1w_256x128_m1_r2c2/ot_sram_1r1w_256x128_m1_r2c2.v
 $M/ot_sram_1r1w_64x128_m1_r2c2/ot_sram_1r1w_64x128_m1_r2c2.v"
if [ ! -x "$OUT/obj/Vtb" ]; then
"$V" --binary -j 16 --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_qkd_astk_calendar -DKVD_HEADS=1 -DKVD_STMUT=$MUT \
  -DKVD_CAL_STRIDE=$STRIDE -DKVD_RL=$RL -DKVD_DER=$DER -Mdir "$OUT/obj" -o Vtb $SRC > "$OUT/build.log" 2>&1 \
  || { tail -30 "$OUT/build.log"; echo "FAIL qkd_astk_calendar build"; exit 1; }
fi
"$OUT/obj/Vtb" "$@" > "$OUT/run.log" 2>&1 || true
grep -E '^(CAL|PASS|FAIL)' "$OUT/run.log" | head -8
grep -q '^PASS qkd_astk_calendar' "$OUT/run.log"
