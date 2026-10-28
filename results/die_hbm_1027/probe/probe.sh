#!/bin/bash
# DIE-HBM-4 C20f die GRT CONGESTION PROBE (12.14b estimate, NOT a gate): die_trial kit (core abstracts, die-top signals
# M4-M9, clock NDR reservations + PG as obstructions) -> global_route 50 it, -critical_nets_percentage 0, allow_congestion.
set -o pipefail
D=/srv/opentallas-scratch2/claude/die-hbm-1027/c20f_probe; WT=/srv/opentallas-scratch2/claude/wt/die-hbm-1027; T=$WT/tools/die_plan
PLAN=/srv/opentallas-scratch2/claude/die-hbm-1027/c20f/die_plan.json
echo START $(date) src=$(git -C $WT rev-parse --short HEAD) plan=$(sha256sum $PLAN | cut -c1-12)
cd $WT
python3 $T/die_trial.py kit $PLAN --out $D/kit > $D/kit_build.log 2>&1; echo KIT rc=$? $(date)
grep -c "critical_nets_percentage 0" $D/kit/grt/grt.tcl
MEM=200 CPUS=16 bash $D/kit/run_grt.sh; echo GRT rc=$? $(date)
grep -c "GRT-011[34]" $D/kit/grt/grt.log; grep -E "^Total|overflow" $D/kit/grt/grt.log | tail -5
echo ALL_DONE $(date)
