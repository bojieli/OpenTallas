#!/bin/bash
set -euo pipefail
b=/srv/opentallas-scratch2/claude/codex-s81-2340/global_clock_src
cd "$b"
reg=$(python3 -c 'import json;print(",".join(sorted(set(json.load(open("map398.json"))["part_region"].values()))))')
python3 tools/die_plan/die_trial.py kit plan_s13r2.json --out geometry01 --leaf-um 200 --rep-um 250 --tree-form link_htree --feed feed_sb6.json --region-trees map398.json --tree-site-legal --tree-site-slide --region-dme delay --region-dme-only "$reg" --region-dme-early .9324 --region-dme-early-mode merge --region-dme-snake all --clock-cell inv2 --region-dme-stage-cal bk_stage_cal_2w2s_late.json --tree-opt dme_feed_centroid=1 --cell-paths --region-dme-workers 24 --region-dme-actual-max 405 --rep-actual-max 405 > geometry01.log 2>&1
