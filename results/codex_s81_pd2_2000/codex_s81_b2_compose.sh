#!/bin/bash
set -euo pipefail
O=/srv/opentallas-scratch2/claude/codex-s81-pd2-2000
cd "$O/modelsrc"
P=$O/b2_candidate/die_plan_pd2_b2_candidate.json
python3 tools/die_plan/gen.py latency "$P" --inplace --out "$O/b2_candidate/gen_lat_base" > "$O/b2_candidate/gen_lat_base.log" 2>&1
python3 tools/die_plan/fallback_regions.py plan "$P" --lat "$O/b2_candidate/gen_lat_base/s81_latency.json" --out "$O/b2_candidate/regions" --block 2 --core tap --hard-merge inputs --groups /srv/opentallas-scratch2/claude/wt/codex-s81-pd2-2000/results/path_s81_pd_1026/scripts/svc_groups.json > "$O/b2_candidate/regions.log" 2>&1
python3 /srv/opentallas-scratch2/claude/wt/codex-s81-pd2-2000/results/fallback_s81_1026/compose_plan.py "$P" "$O/b2_candidate/regions/landed_crossings.json" "$O/b2_candidate/die_plan_pd2_b2_composed.json" "$O/b2_candidate/side.json" > "$O/b2_candidate/compose.log" 2>&1
python3 tools/die_plan/gen.py latency "$O/b2_candidate/die_plan_pd2_b2_composed.json" --inplace --out "$O/b2_candidate/gen_lat_composed" > "$O/b2_candidate/gen_lat_composed.log" 2>&1
python3 tools/die_plan/check.py "$O/b2_candidate/die_plan_pd2_b2_composed.json" --out "$O/b2_candidate/g0" > "$O/b2_candidate/g0.log" 2>&1 || true
