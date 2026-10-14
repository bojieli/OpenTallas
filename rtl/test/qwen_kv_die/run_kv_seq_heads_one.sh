#!/usr/bin/env bash
# el1014-qwen-kvsys-elements: ONE profile of tb_kv_seq_heads (closure-loop bench form; run_kv_seq_heads.sh runs all).
#   run_kv_seq_heads_one.sh OUT HEADS_QFP32_MUT_CLUSTER   e.g. 1_1_0_2 = native TP8 masters (qkd_seq_tp8), exact
#   env CORE_MUT=n: the core body's mutant n (2 = Q beat swap, 4 = OR join) inside the native core
# Prints the tb verdict line; exit 0 iff EXACT_PASS (a mutant profile therefore exits 1 = the loop's expected fail).
set -u
OUT=$1; P=$2
cd "$(dirname "$0")/../../.."
mkdir -p "$OUT"
IFS=_ read -r heads precision mutant cluster <<< "$P"
nd=(); [ "$cluster" = 2 ] && nd=(-DNATIVE_MASTER)
[ -n "${CORE_MUT:-}" ] && nd+=(-DOT_QKD_SEQ_CORE_MUTN=$CORE_MUT)   # body mutant inside the (native) core
iverilog "${nd[@]}" -g2012 -s tb_kv_seq_heads -Ptb_kv_seq_heads.HEADS="$heads" -Ptb_kv_seq_heads.Q_FP32="$precision" \
  -Ptb_kv_seq_heads.MUT="$mutant" -Ptb_kv_seq_heads.CLUSTER="$cluster" -o "$OUT/sim_$P" \
  rtl/test/qwen_kv_die/tb_kv_seq_heads.sv rtl/qwen_sys/kv_die_20261009/ot_qkvd_kv_seq_merged.sv \
  rtl/qwen_sys/kv_die_20261009/ot_qkvd_fifo.sv rtl/qwen_sys/kv_die_20261009/ot_qkvd_kv_desc.sv \
  rtl/qwen_sys/system_20261008/ot_qfd_dctl.sv rtl/physical/ot_qwen_kv_centre_slots.sv rtl/physical/ot_qwen_kv_seq_tp8.sv \
  rtl/lib/ot_rst_relay.sv > "$OUT/compile_$P.log" 2>&1 || { tail -5 "$OUT/compile_$P.log"; echo "BUILD_FAIL $P"; exit 3; }
vvp "$OUT/sim_$P" > "$OUT/run_$P.log" 2>&1
grep -E '^EXACT_(PASS|FAIL|TIMEOUT)|ERROR:' "$OUT/run_$P.log" | head -3
grep -Eq '^EXACT_PASS ' "$OUT/run_$P.log" && ! grep -Eq 'EXACT_FAIL|EXACT_TIMEOUT|ERROR:' "$OUT/run_$P.log"
