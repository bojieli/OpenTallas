#!/bin/bash
# DIE-S81-5 variant C = A + legal detours on every leg with an unrepeated straight span > 1.6 x rep_um (kit_detour.py)
WT=/srv/opentallas-scratch2/claude/wt/die-s81-5; O=/srv/opentallas-scratch2/claude/die-s81-5
echo START $(date) code $(git -C $WT rev-parse --short HEAD) plan $(sha256sum $O/plan_s5.json | cut -c1-12)
python3 $WT/results/die_s81_5_1028/scripts/kit_detour.py 1.6 kit $O/plan_s5.json --out $O/kit_C --leaf-um 200 --rep-um 250 \
  --tree-form link_htree --feed $O/feed/feed_part_spine.json --region-trees $O/feed/map_part.json --tree-site-slide
echo KIT_RC $? $(date)
