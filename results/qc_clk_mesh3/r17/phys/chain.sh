#!/bin/bash
# INFRA-FIRST-QC-R17 physical clock build (d43b, 43.2 delta die): combo GRT (kit + fixed clock) -> RCX ndr016 -> DRC
# (drt::check_drc on every clock box) + STA TT/FF native/rcx -> route report + DRC classes.  Peak = DRC 48 + 4 x STA 16.
set -uo pipefail
B=/srv/opentallas-scratch2/claude/qc-mesh-r17/pkg/build
W=/srv/opentallas-scratch2/claude/wt/qc-mesh-r17-1027
export PYTHONPATH=$W/tools/die_plan:/srv/opentallas-scratch2/claude/die-proto-2325/pylib
echo "START $(date)"
COMBO_MEM=48 MEM=64 DRC_MEM=48 STA_MEM=16 bash $B/tree/run_route.sh > $B/route_actual.log 2>&1; rc=$?
echo "run_route rc $rc $(date)"
python3 $W/tools/die_plan/clock_routed.py report $B/tree > $B/report.out 2>&1; echo "report rc $?"
python3 /srv/opentallas-scratch2/claude/clock128-r8-1026/drccls.py $B/tree/drc $B/tree $B/drccls.json > $B/drccls.txt 2>&1; echo "drccls rc $?"
echo "R17_BUILD_DONE rc $rc $(date)"
exit $rc
