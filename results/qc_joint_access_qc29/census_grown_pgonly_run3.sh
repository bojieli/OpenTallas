#!/bin/bash
cd /srv/opentallas-scratch2/claude/die-qc29/census_grow
python3 /srv/opentallas-scratch2/claude/wt/die-qc29-1029/results/qc_clock_physical_1029/native_landing_plan.py --endpoints endpoints_grown.json --clock-plan /srv/opentallas-scratch2/claude/codex-qc-mesh5-1029/joint_groups_actual/repair_plan.json --pg /srv/opentallas-scratch2/claude/codex-qc-mesh5-1029/census119_h800/pg_rects.json --spacing 0.32 --out grown_pgonly
