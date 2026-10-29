#!/bin/bash
# DIE-KV-12: kit.sh with a repeater spacing: kit2.sh TAG CELL REP_UM  (die_trial from DIE-QC-11 1465eff51c, qc11/, no fork)
T=$1; V=$2; REP=$3; R=/srv/opentallas-scratch2/claude/die-kv-15-1028
python3 $R/qc11/tools/die_plan/die_trial.py kit /srv/opentallas-scratch2/claude/die-kv-15-1028/hm_r26q15c.json --out $R/kit_$T \
  --region-trees /srv/opentallas-scratch2/claude/die-kv-2-1027/l128/land128_regions.json --feed /srv/opentallas-scratch2/claude/die-kv-15-1028/feed_fishbone.json \
  --tree-form link_htree --leaf-um 200 --rep-um $REP --tree-site-legal --tree-site-slide \
  --tap-pad /srv/opentallas-scratch2/claude/die-kv-5-1027/pad/pad_it2.json --clock-cell $V
