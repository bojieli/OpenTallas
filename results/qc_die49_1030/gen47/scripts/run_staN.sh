#!/bin/bash
# DIE-QC-49/gen47: main die_sta_related.py (shared model, same args as DIE-QC-45 run_sta.sh) on the gen47 source-rebuilt
# GRT-routed proof. usage: run_sta.sh NAME [extra args]
set -u
N=$1; shift; R=/srv/opentallas-scratch2/claude/die-qc-49/g47src; T=$R/tools_die_plan
cd $R
systemd-run --user --scope -q -p MemoryMax=64G env PYTHONPATH=$T python3 -I $T/die_sta_related.py $R/proofN --plan $R/plan_qc49.json --out $R/sta_$N --corner TT --corner FF --cppr-lca --clock-ocv table --clock-droop shared --droop-regions $R/proofN/droop_regions.json --clock-cal spice_edge "$@" > $R/sta_$N.log 2>&1
echo "rc=$? $(date)" > $R/sta_$N.status
