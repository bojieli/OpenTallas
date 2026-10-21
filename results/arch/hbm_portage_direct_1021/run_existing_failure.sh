#!/bin/bash
set -euo pipefail
B=/srv/opentallas-scratch/claude/codex-hbm-r14-recovered-1021/chainB
O=/srv/opentallas-scratch/claude/codex-hbm-portage-fix-eaccb9ab1-1021
cd $B/src_d9d30fa7a
python3 $O/relay_layer_d4f.py --stations $B/artifacts/stations_lanes.json --contract $B/artifacts/net/pre_relay.json --manifest $B/a/case_a/manifest.json --root-sites $B/artifacts/root_sites.json --region-map results/arch/hbm_release_r14_1021/planB_margin/d4g_region_map.json --exclude-re '^(rfr|sfr)_' --fork-lane-width 136 --lane-rows --land --port-age-land --land-plan results/arch/hbm_die_d4g/landing/land_plan_d4g.json --out $O/layer.json.gz --report $O/layer_report.json
python3 tools/hbm_die_v16/d4g_relay_splice.py $B/artifacts/net/pre_relay.json $O/layer.json.gz $O/contract.json --report $O/splice.json
python3 tools/hbm_die_v16/d4g_layers/l7_wire.py $O/contract.json $O/l7.json --report $O/l7_report.json
printf '%s\n' PORTAGE_EXISTING_FAILURE_REPLAY_DONE_NO_ROUTE
