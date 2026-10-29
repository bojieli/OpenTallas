#!/bin/bash
# DIE-S81-5 variant F = E on DIE-QC-3 claude/die-qc3b-1027@2de66bb213 (--clock-rc 1x --region-dme delay, COORD 01:4x)
WT=/srv/opentallas-scratch2/claude/wt/die-s81-5-qc3b; S5=/srv/opentallas-scratch2/claude/wt/die-s81-5; export OT_KIT_WT=$WT; O=/srv/opentallas-scratch2/claude/die-s81-5
echo START $(date) code $(git -C $WT rev-parse --short HEAD) plan $(sha256sum $O/plan_s5.json | cut -c1-12)
python3 $S5/results/die_s81_5_1028/scripts/kit_detour.py 1.6 kit $O/plan_s5.json --out $O/kit_F --leaf-um 200 --rep-um 250 \
  --tree-form link_htree --feed $O/feed/feed_part_spine.json --region-trees $O/feed/map_part.json --tree-site-slide --clock-rc 1x --region-dme delay
echo KIT_RC $? $(date)
