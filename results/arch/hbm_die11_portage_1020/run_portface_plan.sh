#!/bin/bash
set -euo pipefail
cd src
P=/srv/opentallas-scratch/claude/hbm-die10-1020/planA
python3 tools/hbm_die_v16/relay_lanes_d4f.py --stations $P/artifacts/stations_case_a_405.json --pins $P/artifacts/pins.json.gz --contract $P/a/views/contract.json --manifest $P/a/case_a/manifest.json --root-keepouts $P/artifacts/root_sites.json --jobs 16 --capacity --split-port-faces --out ../portface_stations.json --report ../portface_plan_report.json
python3 tools/hbm_die_v16/relay_layer_d4f.py --stations ../portface_stations.json --contract $P/a/views/contract.json --manifest $P/a/case_a/manifest.json --root-sites $P/artifacts/root_sites.json --region-map results/arch/hbm_die_d4g/gen2e4r9_1020/planA/d4g_region_map.json --exclude-re '^(rfr|sfr)_' --fork-lane-width 136 --lane-rows --land --port-age-land --land-plan results/arch/hbm_die_d4g/landing/land_plan_d4g.json --out ../portface_layer.json.gz --report ../portface_layer_report.json
python3 - <<'PY'
import json
r=json.load(open('../portface_plan_report.json'));l=json.load(open('../portface_layer_report.json'))
print('PORTFACE_RESULT', 'split',sum(x['status']=='split' for x in r['port_face_split']),'unresolved',sum(x['status']=='kept_unresolved' for x in r['port_face_split']), 'hop_violations',r['hop_violations'],'layer_over',len(l['hops_over_reach']),'problems',l['problems'],'unknown_E',l['landing']['no_E'])
PY
