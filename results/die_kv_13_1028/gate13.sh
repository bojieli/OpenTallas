#!/bin/bash
# DIE-KV-13 gate on the ECTL-equalised inverter phase bind (ev1/bind.json): die_sta_related as DIE-KV-12 ca.sh, tools = TOOLS dir
set -u
B=$1; O=$2; S=${3:-/srv/opentallas-scratch2/claude/wt/die-kv-6/tools/die_plan}
R12=/srv/opentallas-scratch2/claude/die-kv-12-1028; P=$R12/proof_inv_r150; PL=/srv/opentallas-scratch2/claude/die-kv-4-1027/pd9c/hm_r26q9c.json
mkdir -p $O; cp -r /srv/opentallas-scratch2/claude/die-kv-6-1028/sta_region/regchar $O/ 2>/dev/null
python3 $S/die_sta_related.py $P --plan $PL --out $O --clock-cal spice --cppr-lca --count-align $B --count-align-key region --clock-ocv table --clock-droop shared --droop-regions $P/droop_regions.json --hold-buffers HB4 --core-latency-ff 202.5 > $O.log 2>&1; echo STA_RC $? $(date -Is)
