#!/bin/bash
set -euo pipefail
cd src
P=/srv/opentallas-scratch/claude/hbm-die10-1020/planA
python3 tools/hbm_die_v16/relay_layer_d4f.py --stations ../freechannel_stations.json --contract $P/a/views/contract.json --manifest $P/a/case_a/manifest.json --root-sites $P/artifacts/root_sites.json --region-map results/arch/hbm_die_d4g/gen2e4r9_1020/planA/d4g_region_map.json --exclude-re '^(rfr|sfr)_' --fork-lane-width 136 --lane-rows --land --port-age-land --land-plan results/arch/hbm_die_d4g/landing/land_plan_d4g.json --out ../freechannel_unique_layer.json.gz --report ../freechannel_unique_layer_report.json
cd ..
python3 inventory_oracle.py freechannel_unique_layer.json.gz
