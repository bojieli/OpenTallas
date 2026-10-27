#!/bin/bash
# TOK-DS-9b: run every case dir in parallel on the existing tb_vpx_ag binary (sources sha-identical to main 0f9789993e)
set -u; O=$1; shift
for C in "$@"; do ( bash tools/s81_dv/layer_prog/vpx/run_vpx_ag.sh $O $C > $C/case.out 2>&1; echo "rc $?" >> $C/case.out ) & done; wait
for C in "$@"; do echo "$(basename $C): $(grep -m1 CASE $C/case.out | cut -c1-220) | $(tail -1 $C/case.out)"; done
