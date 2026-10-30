#!/bin/bash
set -eu
cd /srv/opentallas-scratch2/claude/codex-kv-2249
mkdir proof_components_data_only
cp proof_loaded/{mesh.json,droop_regions.json} proof_components_data_only/
for C in TT FF; do
 python3 src/tools/die_plan/trial_tap_arrivals.py /srv/opentallas-scratch2/claude/die-kv-42-1029/stgrt/clkgrt_st/tree.json edges_$C/arr_$C.txt "$C" proof_components_data_only/tap_arrivals_$C.json --node-cell-names --clock-components >components_export_$C.txt
done
python3 - <<'PY'
import json
x=json.load(open('nativeB_full.json'));x['start_ports']={};x['diagnostic_scope']='DATA CA ONLY: START omitted deliberately; cannot establish die gate'
json.dump(x,open('nativeB_data_only_diagnostic.json','w'))
PY
sed -e 's/proof_all_loaded/proof_components_data_only/g' -e 's/sta_all_loaded_/sta_components_DATA_ONLY_/g' -e 's/nativeB_full.json/nativeB_data_only_diagnostic.json/g' gate_all_loaded.sh > gate_components_DATA_ONLY.sh
bash gate_components_DATA_ONLY.sh spice_cell
