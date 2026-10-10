#!/bin/bash
# kv-die 2026-10-09 (review-1149 KV14): the KV-die write path bench (tb_qkvd_kv_wq.sv), base + mutants 1-4 + a long run
# (144 rows = 36 layers x 4, controller latency 40 hclk).  DIST=1 (env, redesign-qwen): the distributed successor.  kv_wq_bench.sh <out dir>  -> <out>/results.jsonl
set -u
O=$(readlink -f $1); mkdir -p $O
W=$(cd "$(dirname "$0")/../.." && pwd)
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
SRC="$W/qwen_sys/emb_hbm_20261008/ot_qfd_emb_pkg.sv $W/qwen_sys/emb_hbm_20261008/ot_qfd_emb_pcport.sv $W/hdc/kv/ot_qwen_stream4_cdc_pc.sv $W/qwen_sys/kv_die_20261009/ot_qkvd_kv_wq.sv $W/qwen_sys/kv_die_20261009/ot_qkvd_kv_wq_dist.sv $W/qwen_sys/kv_die_20261009/ot_qkvd_kv_wq_tiles.sv $W/qwen_sys/kv_die_20261009/ot_qkvd_kv_wq_tiles_top.sv $W/hdc/ot_hdc_delay.sv $W/test/qwen_kv_die/tb_qkvd_kv_wq.sv"
: > $O/results.jsonl
for v in "base -GMUT=0" "mut1 -GMUT=1" "mut2 -GMUT=2" "mut3 -GMUT=3" "mut4 -GMUT=4" "long -GNROW=144 -GCTRL_LAT=40"; do
  set -- $v; n=$1; shift
  $VL --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_qkvd_kv_wq -GDIST=${DIST:-0} "$@" $SRC \
      --Mdir $O/obj_$n -o Vtb > $O/build_$n.log 2>&1 || { echo "{\"run\": \"$n\", \"build_rc\": $?}" >> $O/results.jsonl; continue; }
  r=$($O/obj_$n/Vtb 2>/dev/null | grep '"mut"')
  echo "{\"run\": \"$n\", \"res\": ${r:-null}}" >> $O/results.jsonl
done
cat $O/results.jsonl
