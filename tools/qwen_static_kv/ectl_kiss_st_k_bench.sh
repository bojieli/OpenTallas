#!/bin/bash
# KV-ECTL4 2026-10-18: the static K path of the ECTL frame the die binds (qkd_ectl3_kiss_st = A qkd_static_ectla_kiss +
# B + C qkd_ectl_c_st) at the DIE configuration: one K round trip RL (die 80: kv_k_rt_eq pads every frame's request
# chain) and QK_ISSUE_AGE QK (die 91 = RL + 11).  36 layers of tb_qkd_static_k_issuer (+define+OT_KISS_ST): every request
# at its calendar slot with its tag / epoch / layer, every landing response RL edges later, every K issue at
# start + QK + scan, every consumed SRAM row bit-exact, no fault.
# usage: [RL=80 QK=91] ectl_kiss_st_k_bench.sh OUTDIR [MUT]
#   MUT 0 PASS; 5 layer identity (FAIL 'request identity'); 8 landing one edge late (FAIL 'late landing response faulted');
#   9 frame built with QK_ISSUE_AGE = QK - 1 (FAIL 'consume slot')
set -e
R=$(cd "$(dirname "$0")/../.." && pwd); OUT=$1; MUT=${2:-0}; RL=${RL:-80}; QK=${QK:-91}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
[ -x "$V" ] || V=$(command -v verilator)
mkdir -p "$OUT"
S=$R/rtl/qwen_sys/split_20261014; K=$R/rtl/qwen_sys/static_kv_20261014
SRC="$R/rtl/test/qwen_static_kv/tb_qkd_static_k_issuer.sv $K/qkd_static_ectl_st.sv $K/qkd_ectl_c_st.sv $K/qkd_static_ectla_kiss.sv $K/qkd_static_k_issuer.sv
 $S/qkd_ectl3_epoch_direct_s.sv $S/qkd_ectl_a_tp8_epoch_direct.sv $S/qkd_ectl_native_direct_tp8.sv $R/rtl/hdc/nearhbm/ot_qkd_ectl_parts.sv
 $R/rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_h.sv $R/rtl/hdc/ot_hdc_delay.sv $R/rtl/lib/ot_rst_relay.sv
 $R/physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v"
"$V" --version
"$V" --binary -j 8 --timing -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_qkd_static_k_issuer +define+OT_KISS_ST \
  -GMUT=$MUT -GRL=$RL -GQK=$QK -Mdir "$OUT/obj" -o Vtb $SRC > "$OUT/build.log" 2>&1 || { tail -30 "$OUT/build.log"; echo "FAIL ectl_kiss_st_k build"; exit 1; }
"$OUT/obj/Vtb" > "$OUT/run.log" 2>&1 || true
tail -4 "$OUT/run.log"
n=$(grep -c '^STATIC_K PASS' "$OUT/run.log" || true)
if [ "$n" = 36 ] && ! grep -qiE 'fatal|error' "$OUT/run.log"; then echo "PASS ectl_kiss_st_k RL $RL QK $QK mut $MUT: 36 layers"; else echo "FAIL ectl_kiss_st_k RL $RL QK $QK mut $MUT: $n layers"; exit 1; fi
