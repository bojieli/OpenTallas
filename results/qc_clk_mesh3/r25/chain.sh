#!/bin/bash
# INFRA-FIRST-QC-R25 task 4: guard51 die clock DRC re-run on the R24b M9 wide-VSS fix (TrackRouter merged_width over drawn
# shields; dry build = qc-mesh-r24/dryfix/dry, plan sha 37937a86).  clock-alone kit -> combo --routed-clock (TT) -> route
# (DRT keeps fixed clock wires) + RCX -> DRC on every clock box + STA -> route report + DRC classes (incl. the same-net
# 0.04-um shield gaps).  Same chain as R17 (epyc2 qc-mesh-r17/pkg/build/chain.sh).
set -uo pipefail
B=/srv/opentallas-scratch2/claude/qc-mesh-r25/drc
W=/srv/opentallas-scratch2/claude/wt/qc-mesh-r25-1027
P=/srv/opentallas-scratch2/claude/codex-qwen-1027/pkg
export PYTHONPATH=$W/tools/die_plan:/srv/opentallas-scratch2/claude/die-proto-2325/pylib
echo "START $(date)"
[ -s $B/clockkit/kit.json ] || python3 $W/tools/die_plan/die_infra.py clockkit $P/inputs/d51/plan_d43.json --kit $P/out/guard51/basekit --out $B/clockkit > $B/clockkit.log 2>&1 || exit 3
[ -s $B/tree/combo.tcl ] || python3 $W/tools/die_plan/die_clock_mesh.py combo $B/tree --kit $B/clockkit --plan $P/inputs/d51/plan_d43.json --routed-clock > $B/combo.log 2>&1 || exit 4
[ -s $B/tree/run_route.sh ] || python3 $W/tools/die_plan/clock_routed.py route $B/tree --kit $B/clockkit > $B/routegen.log 2>&1 || exit 5
COMBO_MEM=48 MEM=64 DRC_MEM=48 STA_MEM=16 bash $B/tree/run_route.sh > $B/route_actual.log 2>&1; rc=$?
echo "run_route rc $rc $(date)"
python3 $W/tools/die_plan/clock_routed.py report $B/tree > $B/report.out 2>&1; echo "report rc $?"
python3 $B/drccls.py $B/tree/drc $B/tree $B/drccls.json > $B/drccls.txt 2>&1; echo "drccls rc $?"
python3 $B/r25_samenet_gaps.py $B/tree/mesh.json $B/tree/drc $B/samenet_gaps_drc.json > $B/samenet.txt 2>&1; echo "samenet rc $?"
echo "R25_DRC_DONE rc $rc $(date)"
exit $rc
