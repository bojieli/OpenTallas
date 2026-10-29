#!/bin/bash
# DIE-KV-25: DIE-KV-21 tree c recipe (kit3.sh + DME pv_S_6/7 delay + kv_cal_fit_b) on MAIN 2b90210bd die_trial. usage: kit.sh TAG PLAN
T=$1; PL=$2; R=/srv/opentallas-scratch2/claude/die-kv-25-1029; W=/srv/opentallas-scratch2/claude/wt/die-kv-25
python3 $W/tools/die_plan/die_trial.py kit $PL --out $R/kit_$T \
  --region-trees /srv/opentallas-scratch2/claude/die-kv-2-1027/l128/land128_regions.json --feed /srv/opentallas-scratch2/claude/die-kv-15-1028/feed_fishbone.json \
  --tree-form link_htree --leaf-um 200 --rep-um 150 --tree-site-legal --tree-site-slide \
  --tap-pad /srv/opentallas-scratch2/claude/die-kv-20-1028/pad_kv20_pad.json --clock-cell inv \
  --region-dme delay --region-dme-only pv_S_6,pv_S_7 --region-dme-stage-cal /srv/opentallas-scratch2/claude/die-kv-21-1028/kv_cal_fit_b.json
echo KIT_${T}_RC $? $(date)
