#!/bin/bash
# DIE-S81-5 variant B: region = partition (398) link_htree on the locality spine feed, leaf 200 / rep 250, --tree-site-slide (main balance_legalize as-is) --tree-opt full=1
WT=/srv/opentallas-scratch2/claude/wt/die-s81-5; O=/srv/opentallas-scratch2/claude/die-s81-5
echo START $(date) code $(git -C $WT rev-parse --short HEAD) plan $(sha256sum $O/plan_s5.json | cut -c1-12)
python3 $WT/tools/die_plan/die_trial.py kit $O/plan_s5.json --out $O/kit_B --leaf-um 200 --rep-um 250 \
  --tree-form link_htree --feed $O/feed/feed_part_spine.json --region-trees $O/feed/map_part.json --tree-site-slide --tree-opt full=1
echo KIT_RC $? $(date)
