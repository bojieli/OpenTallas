#!/bin/bash
# LAND-S81-1: region-tree kit on the composed landed plan, equal-latency region trunks (--region-equal), sl300 recipe + 405-um repeaters; render
set -eu
WT=/srv/opentallas-scratch2/claude/wt/land-s81-1027; O=/srv/opentallas-scratch2/claude/land-s81-1027; J=${J:-$WT/physical/die_plan/s81/die_plan_land.json}
cd $WT
echo START $(date) host $(hostname) code $(git rev-parse --short HEAD) plan $(sha256sum $J | cut -c1-12)
python3 tools/die_plan/die_trial.py kit $J --out $O/kit --htree-full-depth --leaf-um 300 --rep-um 405 --tree-site-slide \
  --region-trees $O/reg/regions.json > $O/kit_build.log 2>&1
python3 results/land_s81_1027/scripts/render_regions_tree.py $J $O/reg/regions.json $O/kit/clock/tree.json $O/kit/tree_regions.png $O/kit/tree_summary.json > $O/render.log 2>&1
python3 -c "import json;m=json.load(open('$O/kit/clock/tree.json'))['meta'];e=m.pop('region_equal',{});e.pop('per_region',None);print(json.dumps(m));print(json.dumps(e))"
echo KIT_DONE $(date)
