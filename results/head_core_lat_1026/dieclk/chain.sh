#!/bin/bash
# usage: chain.sh DIR   (ISLAND_STRICT env passes through)
set -e
D=$1; export PYTHONPATH=/srv/opentallas-scratch2/claude/codex-head-clock-1026/pylib
T="python3 /srv/opentallas-scratch2/claude/wt/head-core-lat-dieclk-1026/tools/s81_head/island_clock_mesh.py --spec /srv/opentallas-scratch2/claude/wt/head-core-lat-dieclk-1026/results/head_core_lat_1026/island_spec.json"
PLAN=/srv/opentallas-scratch2/claude/wt/head-core-lat-dieclk-1026/physical/die_plan/s81_head/die_plan.json
$T build $PLAN --out $D --nx 32 --ny 32 --m 2 --reserve-cell-sites > $D/build.log 2>&1
python3 - $D/mesh.json <<PY
import json,sys
M=json.load(open(sys.argv[1]))
s=[u for u in M["unplaced"] if len(u)>2 and "STRUCTURAL" in str(u[2]) and "t_lk_" in str(u[1])]
rest=[u for u in M["unplaced"] if u not in s]
print("unplaced serdes-PHY-structural", len(s), "other", len(rest), rest[:5])
M["structural_measured_unsplit"]=s; M["unplaced"]=rest; M["meta"]["unplaced"]=len(rest)
M["meta"]["model_assumption_2"]="serdes PHY-interior taps left as direct unsplit tails for measurement only (STRUCTURAL)"
json.dump(M,open(sys.argv[1],"w"))
PY
$T combo $D --kit /srv/opentallas-scratch2/claude/codex-head-clock-1026/kit --plan $PLAN
MEM=48 bash $D/run_combo.sh
bash /srv/opentallas-scratch2/claude/head-core-lat-1026/dieclk/island_post.sh $D $PLAN
