#!/bin/bash
# HBM-CORE-LAT-R4 hcp_sys1 chain on the UNCHANGED plan-built clock (4_cts.odb from cts_r4.sh):
# run_kit_hbm.sh GOAL=route (hold gate -> GRT BC data-hold repair -> per-corner insertion gate TT/FF -> DRT -> finish ->
# abstract -> corners -> signoff.py tt,ff), then LEC of the ROUTED netlist (6_final.v) vs kit RTL.
set -uo pipefail
K=$(cd "$(dirname "$0")" && pwd)
st(){ echo "R4CHAIN $* $(date -Is)" | tee -a $K/route_r4.status; }
st start
bash $K/run_kit_hbm.sh $K route 24 8; rc=$?; st run_kit rc $rc
F=$(ls $K/run/results/asap7/*/base/6_final.v 2>/dev/null | head -1)
if [ -n "$F" ]; then python3 -I $K/lec.py.r4-not-in-cts-run $K --netlist $F --out $K/lec_routed --jobs 8 --mem 32 > $K/lec_routed.log 2>&1; lr=$?; st lec_routed rc $lr $(tail -1 $K/lec_routed.log); fi
exit $rc
