#!/bin/bash
set -u
Q=/srv/opentallas-scratch2/claude
W=$Q/wt/codex-qc-clock-0336
R=$Q/codex-qc-clock-0336
python3 -I "$W/tools/die_plan/die_sta_related.py" "$R/proof_actual" --plan "$Q/die-qc-46/plan/plan_qc45.json" --out "$R/sta_ca" --corner TT --corner FF --cppr-lca --clock-ocv table --clock-droop shared --droop-regions "$R/proof_actual/droop_regions.json" --clock-cal spice_edge --count-align "$R/ca/plan_bind_full.json" --count-align-key region --count-align-ss-scale 0 > "$R/sta_ca.log" 2>&1
rc=$?
echo "rc=$rc $(date -Is)" > "$R/sta_ca.status"
exit $rc
