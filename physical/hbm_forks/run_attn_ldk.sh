#!/bin/bash
# hbm-forks 2026-10-09 (RQ-HF-4): the split attention tile with the entry-point strap ldk.
#   CF-1: ldk = 0, roles 0..4 lock-stepped against hfd_attn_tile_b (the existing run_lockh.sh, unchanged semantics);
#   ldk = 1: role 4 (every source at once) against hfd_attn_tile_b fed chains with the ld field cleared: PASS;
#   mutant OT_ATTN_MUT_LDK (strap ignored) with ldk = 1: must FAIL.    run_attn_ldk.sh <out dir>
O=$1; mkdir -p $O; rc=0
bash physical/hbm_attn_tile_r/half/run_lockh.sh $O/cf1 pos > $O/cf1.txt 2>&1; tail -n 1 $O/cf1.txt | grep -q "ATTN_LOCKH PASS" || rc=1
echo "cf1: $(tail -n 1 $O/cf1.txt)"
bash physical/hbm_attn_tile_r/half/run_lockh.sh $O/ldk1 pos -GLDK=1 > $O/ldk1.txt 2>&1; tail -n 1 $O/ldk1.txt | grep -q "ATTN_LOCKH PASS" || rc=1
echo "ldk1: $(tail -n 1 $O/ldk1.txt)"
bash physical/hbm_attn_tile_r/half/run_lockh.sh $O/mut pos -GLDK=1 -DOT_ATTN_MUT_LDK > $O/mut.txt 2>&1; tail -n 1 $O/mut.txt | grep -q "ATTN_LOCKH PASS" && rc=1
echo "mut (must FAIL): $(tail -n 1 $O/mut.txt)"
[ $rc -eq 0 ] && echo "ATTN_LDK PASS" || echo "ATTN_LDK FAIL"; exit $rc
