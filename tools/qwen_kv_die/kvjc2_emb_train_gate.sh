#!/usr/bin/env bash
# KVJ-C2: return-train head station (lock-step vs hop with upi 0), 4-train join (exact words + conflict fault) and the
# bridge successor without the gateway SU face (lock-step vs the predecessor, EMBQ arrival faults); every mutant FAILs.
set -euo pipefail
cd "$(dirname "$0")/../..";out=${1:?out};mkdir -p "$out";out=$(cd "$out"&&pwd);export TMPDIR="$out"
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
E=rtl/qwen_sys/static_embedding_20261014;S=rtl/qwen_sys/split_20261014;T=rtl/test/qwen_static_kv
run(){ # name top define muts... -- sources
 local n=$1 top=$2 def=$3;shift 3;local ms=();while [[ $1 != -- ]];do ms+=("$1");shift;done;shift
 for m in "${ms[@]}";do
  "$v" --binary --timing -O1 -Wno-fatal --top-module $top -D$def=$m --Mdir "$out/$n$m-obj" "$@" > "$out/$n$m-build.log" 2>&1
  "$out/$n$m-obj/V$top" > "$out/$n$m.log" 2>&1 || true
  echo "== $n MUT $m: $(grep -E '^(PASS|FAIL)' "$out/$n$m.log" | head -1)"
  if [[ $m == 0 ]];then grep -q '^PASS' "$out/$n$m.log";! grep -q '^FAIL' "$out/$n$m.log";else grep -q '^FAIL' "$out/$n$m.log";fi
 done; }
run head tb_qkd_embedding_return_head OT_KVJ_HEAD_MUT 0 1 -- $E/qkd_embedding_static_return_hop.sv $E/qkd_embedding_static_return_head.sv $T/tb_qkd_embedding_return_head.sv
run join4 tb_qkd_embedding_static_join4 OT_KVJ_J4_MUT 0 1 2 -- $E/qkd_embedding_static_join.sv $E/qkd_embedding_static_join4.sv $T/tb_qkd_embedding_static_join4.sv
run lnk tb_ot_qkvd_split_kvlink_se OT_KVJ_LNK_MUT 0 2 -- rtl/qwen_sys/kv_die_20261009/ot_qkvd_fifo.sv $S/ot_qwen_split_lvl.sv $S/ot_qkvd_split_kvlink.sv $S/ot_qkvd_split_kvlink_se.sv $T/tb_ot_qkvd_split_kvlink_se.sv
echo PASS KVJC2_EMB_TRAIN_HEAD_JOIN4_KVLINK_SE
