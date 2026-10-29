#!/bin/bash
set -e
cd /srv/opentallas-scratch2/claude/die-qc29/census_grow
python3 -I /srv/opentallas-scratch2/claude/wt/die-qc29-1029/results/qc_joint_access_qc29/grow_endpoints.py /srv/opentallas-scratch2/claude/codex-qc-mesh5-1029/census119_h800/endpoints.json /srv/opentallas-scratch2/claude/codex-qc-mesh5-1029/native_growth/growth_candidate.json endpoints_grown.json
for v in base grown; do
 ep=$([ $v = base ] && echo /srv/opentallas-scratch2/claude/codex-qc-mesh5-1029/census119_h800/endpoints.json || echo endpoints_grown.json)
 python3 /srv/opentallas-scratch2/claude/wt/die-qc29-1029/results/qc_clock_physical_1029/native_landing_plan.py --endpoints $ep --clock-plan /srv/opentallas-scratch2/claude/codex-qc-mesh5-1029/joint_groups/backbone_plan.json --pg /srv/opentallas-scratch2/claude/codex-qc-mesh5-1029/census119_h800/pg_rects.json --reserved-power /srv/opentallas-scratch2/claude/codex-qc-mesh5-1029/reserved_full_power.json --spacing 0.32 --out $v
done
