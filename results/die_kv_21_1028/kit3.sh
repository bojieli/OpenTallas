#!/bin/bash
# DIE-KV-21: DIE-KV-20 kit2.sh recipe on MAIN die_trial (no fork) + optional extra args: kit3.sh TAG [extra die_trial args]
T=$1; shift; R=/srv/opentallas-scratch2/claude/die-kv-21-1028; Q=/srv/opentallas-scratch2/claude/die-kv-15-1028
python3 $R/main/tools/die_plan/die_trial.py kit $Q/hm_r26q15c.json --out $R/kit_$T \
  --region-trees /srv/opentallas-scratch2/claude/die-kv-2-1027/l128/land128_regions.json --feed $Q/feed_fishbone.json \
  --tree-form link_htree --leaf-um 200 --rep-um 150 --tree-site-legal --tree-site-slide \
  --tap-pad /srv/opentallas-scratch2/claude/die-kv-20-1028/pad_kv20_pad.json --clock-cell inv "$@"
