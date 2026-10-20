#!/bin/bash
set -euo pipefail
cd src
python3 tools/hbm_die_v16/relay_layer_d4f.py --stations /srv/opentallas-scratch/claude/hbm-die10-1020/planA/artifacts/stations_lanes.json --contract /srv/opentallas-scratch/claude/hbm-die10-1020/planA/a/views/contract.json --manifest /srv/opentallas-scratch/claude/hbm-die10-1020/planA/a/case_a/manifest.json --root-sites /srv/opentallas-scratch/claude/hbm-die10-1020/planA/artifacts/root_sites.json --region-map results/arch/hbm_die_d4g/gen2e4r9_1020/planA/d4g_region_map.json --exclude-re '^(rfr|sfr)_' --fork-lane-width 136 --lane-rows --land --land-plan results/arch/hbm_die_d4g/landing/land_plan_d4g.json --out ../default_layer.json.gz --report ../default_report.json
python3 - <<'PY'
import gzip,json
old='/srv/opentallas-scratch/claude/hbm-die10-1020/planA/artifacts/net/'
a=json.load(gzip.open('../default_layer.json.gz'));b=json.load(gzip.open(old+'relays_d4g_land.json.gz'))
assert a==b;print('DEFAULT_LAYER_EXACT_IDENTITY_PASS',len(a['instances']))
a=json.load(open('../default_report.json'));b=json.load(open(old+'relays_d4g_land_report.json'))
assert a==b;print('DEFAULT_REPORT_EXACT_IDENTITY_PASS')
PY
