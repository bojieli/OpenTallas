#!/bin/bash
# HBM-CORE-LAT-R5 collar_idx256r chain on the R5 trial outline: run_kit_hbm.sh GOAL=finish (CTS with the 12.8c trunk ->
# per-corner insertion gate -> GRT/hold repair -> DRT -> finish -> abstract -> corners -> signoff.py tt,ff), then LEC of the
# ROUTED netlist vs kit RTL with OT_LEC_SUPERSET_VEC=1 (COORD RULING HBM-CORE-LAT-R4 (3): lec.json records superset_vec.extra_bits).
set -uo pipefail
K=$(cd "$(dirname "$0")" && pwd)
st(){ echo "R5CHAIN $* $(date -Is)" | tee -a $K/chain_r5.status; }
st start
bash $K/run_kit_hbm.sh $K finish 24 8; rc=$?; st run_kit rc $rc
F=$(ls $K/run/results/asap7/*/base/6_final.v 2>/dev/null | head -1)
if [ -n "$F" ]; then OT_LEC_SUPERSET_VEC=1 python3 -I $K/lec.py $K --netlist $F --out $K/lec_routed --jobs 8 --mem 32 > $K/lec_routed.log 2>&1; lr=$?; st lec_routed rc $lr $(tail -1 $K/lec_routed.log); fi
exit $rc
