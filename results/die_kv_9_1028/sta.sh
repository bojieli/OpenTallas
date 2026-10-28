#!/bin/bash
# DIE-KV-9 step 5: main die_sta_related at CA-OCV-1 07833e2f9 (git archive, no fork) on the DIE-KV-5 pad2 die GRT0 proof
cd /srv/opentallas-scratch2/claude/die-kv-9-1028
for M in table none; do
  mkdir -p sta_$M; cp -r /srv/opentallas-scratch2/claude/die-kv-6-1028/sta_region/regchar sta_$M/ 2>/dev/null
  python3 /srv/opentallas-scratch2/claude/die-kv-9-1028/sta_tools/tools/die_plan/die_sta_related.py /srv/opentallas-scratch2/claude/die-kv-5-1027/proofpad2 --plan /srv/opentallas-scratch2/claude/die-kv-4-1027/pd9c/hm_r26q9c.json --out sta_$M --clock-cal spice --cppr-lca --count-align /srv/opentallas-scratch2/claude/die-kv-5-1027/capad2/pad2_spice_bind_parts.json --count-align-key region --clock-ocv $M --clock-droop shared --droop-regions /srv/opentallas-scratch2/claude/die-kv-5-1027/proofpad2/droop_regions.json --hold-buffers HB4 --core-latency-ff 202.5 > sta_$M.log 2>&1; echo "STA_$M rc=$?" >> sta_$M.log
done
