#!/bin/bash
# DIE-KV-22: DIE-KV-21 gate3.sh run() recipe (main 6a56d5811 die_sta_related, 3 signed views) on proof $2 with count-align bind $3.
set -u; TAG=$1; PF=$2; CA=$3; CAL=$4
O=/srv/opentallas-scratch2/claude/die-kv-22-1028; R=/srv/opentallas-scratch2/claude/die-kv-15-1028
S=/srv/opentallas-scratch2/claude/die-kv-20-1028/main_6a56d5811/tools/die_plan; PL=$R/hm_r26q15c.json; V=/srv/opentallas-scratch2/claude/die-kv-19-1028/views
CV=""; for d in $V/*/view/*; do CV="$CV --core-view $(basename $d)=$d"; done
mkdir -p $O/sta_$TAG; cp -r /srv/opentallas-scratch2/claude/die-kv-6-1028/sta_region/regchar $O/sta_$TAG/ 2>/dev/null
python3 $S/die_sta_related.py $PF --plan $PL --out $O/sta_$TAG --clock-cal $CAL --cppr-lca \
  --count-align $CA --count-align-key region --clock-ocv table --clock-droop shared \
  --droop-regions $PF/droop_regions.json --hold-buffers HB4 --core-latency-ff 202.5 --clock-cell inv $CV --core-insertion view \
  > $O/sta_$TAG.log 2>&1; echo STA_${TAG}_RC $? $(date)
