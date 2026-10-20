#!/bin/bash
# RTL-BUILD-KV/ASTK 2026-10-18: lockstep of the static ECTL frame on the credit-free ASTK ABI (qkd_ectl3_kiss_st, C leaf
# qkd_ectl_c_st) against qkd_ectl3_kiss_s.  usage: [RL=.. QK=..] ectl_st_bench.sh OUTDIR [MUT]   MUT 0: PASS; 1 / 2: FAIL
# KV-ECTL4 10-18: env RL / QK = the frame's RESPONSE_LAT / QK_ISSUE_AGE (die 80 / 91; default 2 / 34)
set -e
R=$(cd "$(dirname "$0")/../.." && pwd); OUT=$1; MUT=${2:-0}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
[ -x "$V" ] || V=$(command -v verilator)
mkdir -p "$OUT"
S=$R/rtl/qwen_sys/split_20261014; K=$R/rtl/qwen_sys/static_kv_20261014
SRC="$R/rtl/test/qwen_static_kv/tb_qkd_ectl3_kiss_st.sv $K/qkd_static_ectl_st.sv $K/qkd_ectl_c_st.sv $K/qkd_static_ectla_kiss.sv $K/qkd_static_k_issuer.sv
 $S/qkd_ectl3_epoch_direct_s.sv $S/qkd_ectl_a_tp8_epoch_direct.sv $S/qkd_ectl_native_direct_tp8.sv $R/rtl/hdc/nearhbm/ot_qkd_ectl_parts.sv
 $R/rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_h.sv $R/rtl/hdc/ot_hdc_delay.sv $R/rtl/lib/ot_rst_relay.sv
 $R/physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v"
"$V" --binary -j 16 --timing -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_qkd_ectl3_kiss_st -DKVD_ECSTMUT=$MUT -GRL=${RL:-2} -GQK=${QK:-34} \
  -Mdir "$OUT/obj" -o Vtb $SRC > "$OUT/build.log" 2>&1 || { tail -30 "$OUT/build.log"; echo "FAIL qkd_ectl3_kiss_st build"; exit 1; }
"$OUT/obj/Vtb" > "$OUT/run.log" 2>&1 || true
grep -E '^(PASS|FAIL|MISMATCH)' "$OUT/run.log" | head -12
grep -q '^PASS qkd_ectl3_kiss_st' "$OUT/run.log"
