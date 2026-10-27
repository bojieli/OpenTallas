#!/bin/bash
# TOK-DS-8: build tb_vpx_ag once on the worktree RTL, then run every case dir in parallel (run_vpx_ag.sh reuses obj).
set -u; O=$1; shift
rm -rf $O/obj; bash tools/s81_dv/layer_prog/vpx/run_vpx_ag.sh $O > $O/build_only.log 2>&1 || { cat $O/build_only.log; exit 3; }
for C in "$@"; do ( bash tools/s81_dv/layer_prog/vpx/run_vpx_ag.sh $O $C > $C/case.out 2>&1; echo "rc $?" >> $C/case.out ) & done; wait
for C in "$@"; do echo "$(basename $C): $(grep -m1 CASE $C/case.out | cut -c1-220) | $(tail -1 $C/case.out)"; done
