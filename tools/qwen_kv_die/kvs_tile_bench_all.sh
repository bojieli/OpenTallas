#!/bin/bash
# kvs_tile_bench_all.sh OUTROOT [TILES="ctl attn emb"] [MUTS="0 1 2 3"]: every kvs tile bench (fleet driver); one line each
O=$1; TS=${2:-ctl attn emb}; MS=${3:-0 1 2 3}
for T in $TS; do for M in $MS; do bash tools/qwen_kv_die/kvs_tile_bench.sh "$O/${T}_m${M}" "$T" "$M" 2000 | tail -1; done; done
