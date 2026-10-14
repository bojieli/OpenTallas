#!/bin/bash
# qkd_lnk (ot_qkvd_split_kvlink) exact bench for its ref_tile job: the native-TP8 decode step through the real link RTL
# (tb_qwen_split_link SPLIT 1, LLR 0 for speed: the bridge is the unit under test).  usage: lnk_bench.sh <outdir> pos|mut
set -u
OUT=$1; MODE=${2:-pos}; H=$(cd "$(dirname "$0")" && pwd)
P=tb_qwen_split_link
if [ "$MODE" = pos ]; then
  r=$($H/run_split_link.sh $OUT -P$P.SPLIT=1 -P$P.LLR=0 -P$P.C_ST=8 -P$P.K_ST=1 -P$P.KVE_SPL=1 -P$P.ENG=200)
  echo "$r"; case "$r" in SPLIT_LINK_PASS*) echo "PASS qkd_lnk exact"; exit 0;; *) echo "FAIL qkd_lnk exact"; exit 1;; esac
else
  r=$($H/run_split_link.sh $OUT -P$P.SPLIT=1 -P$P.LLR=0 -P$P.C_ST=8 -P$P.K_ST=1 -P$P.KVE_SPL=1 -P$P.ENG=200 -P$P.MUT=3)
  echo "$r"; case "$r" in SPLIT_LINK_FAIL*) echo "FAIL qkd_lnk mutant detected"; exit 1;; *) echo "PASS qkd_lnk mutant missed"; exit 0;; esac
fi
