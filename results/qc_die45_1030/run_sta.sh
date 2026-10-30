#!/bin/bash
# DIE-QC-45: main die_sta_related.py (shared model) on the TRIAL1 G2 proof (host python, 64G scope; the tool runs its own
# OpenSTA docker for the pin-register arcs). usage: run_sta.sh NAME [extra args]
set -u
N=$1; shift; R=/srv/opentallas-scratch2/claude/die-qc-45; W=/srv/opentallas-scratch2/claude/wt/die-qc-45
cd $R
systemd-run --user --scope -q -p MemoryMax=64G env PYTHONPATH=$W/tools/die_plan python3 -I $W/tools/die_plan/die_sta_related.py $R/proof --plan $R/plan/plan_qc43.json --out $R/sta_$N --corner TT --corner FF --cppr-lca --clock-ocv table --clock-droop shared --droop-regions $R/proof/droop_regions.json --clock-cal spice_edge "$@" > $R/sta_$N.log 2>&1
echo "rc=$? $(date)" > $R/sta_$N.status
