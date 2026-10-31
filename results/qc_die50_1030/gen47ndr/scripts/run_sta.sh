#!/bin/bash
# DIE-QC-50/gen47ndr: main die_sta_related.py (shared model, DIE-QC-45 args) on a proof dir. usage: run_sta.sh PROOF NAME [extra]
set -u
P=$1; N=$2; shift 2; R=/srv/opentallas-scratch2/claude/die-qc-50/gen47ndr; T=/srv/opentallas-scratch2/claude/wt/die-qc-50-gen47ndr/tools/die_plan
cd $R
systemd-run --user --scope -q -p MemoryMax=64G env PYTHONPATH=$T python3 -I $T/die_sta_related.py $R/$P --plan /srv/opentallas-scratch2/claude/die-qc-49/g47src/plan_qc49.json --out $R/sta_$N --corner TT --corner FF --cppr-lca --clock-ocv table --clock-droop shared --droop-regions $R/$P/droop_regions.json --clock-cal spice_edge "$@" > $R/sta_$N.log 2>&1
echo "rc=$? $(date)" > $R/sta_$N.status
