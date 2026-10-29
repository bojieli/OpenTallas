#!/bin/bash
# DIE-HBM-4 C20f die GRT CONGESTION PROBE with region trees (12.14b estimate, NOT a gate). $1 = tag, $2 = region map
# die_trial kit --region-trees (core abstracts, die-top signals M4-M9, region clock reservations + PG as obstructions)
# -> global_route 50 it, -critical_nets_percentage 0, allow_congestion.
set -o pipefail
TAG=$1; MAP=$2
B=$(cd $(dirname $0) && pwd); D=$B/probe_$TAG; WT=/srv/opentallas-scratch2/claude/wt/die-hbm-4-probe
T=$WT/tools/die_plan; PLAN=$B/c20f/die_plan.json; mkdir -p $D
echo START $TAG $(date) src=$(git -C $WT rev-parse --short HEAD) plan=$(sha256sum $PLAN | cut -c1-12) map=$MAP
while pgrep -f "worktree add --detach $WT" >/dev/null; do sleep 15; done
cd $WT
python3 $T/die_trial.py kit $PLAN --out $D/kit --region-trees $MAP > $D/kit_build.log 2>&1; echo KIT rc=$? $(date)
grep -c "critical_nets_percentage 0" $D/kit/grt/grt.tcl
MEM=200 CPUS=16 bash $D/kit/run_grt.sh; echo GRT rc=$? $(date)
grep -c "GRT-011[34]" $D/kit/grt/grt.log; grep -E "^Total" $D/kit/grt/grt.log | tail -2
echo ALL_DONE $(date)
