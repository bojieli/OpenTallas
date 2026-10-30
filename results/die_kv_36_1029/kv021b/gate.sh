#!/bin/bash
# DIE-KV-36 (copy of DIE-KV-35 gate.sh, from DIE-KV-34 gate.sh, CA bind = arg 4): DIE-KV-27 gate.sh recipe (proofE form) on leaf variant A arrivals; tools = main 49d8a0c889 die_sta_related (die-kv-33-leaf wt)
set -u; TAG=$1; PF=$2; CAL=$3
O=/srv/opentallas-scratch2/claude/die-kv-36-1029; S=/srv/opentallas-scratch2/claude/wt/die-kv-33-leaf/tools/die_plan
CA=${4:-/srv/opentallas-scratch2/claude/die-kv-35-1029/nativeAp/native_bind.json}
PL=/srv/opentallas-scratch2/claude/die-kv-26-1029/plan_e26a.json
CV=""; for n in 1 2 5 6; do M=kv3_head_eighth_e$n; CV="$CV --core-view $M=/srv/opentallas-scratch2/claude/autopilot/closed/qwen_kvsys/${M}__3e7fccd216/view/$M"; done
mkdir -p $O/sta_$TAG; cp -r /srv/opentallas-scratch2/claude/die-kv-6-1028/sta_region/regchar $O/sta_$TAG/ 2>/dev/null
python3 $S/die_sta_related.py $PF --plan $PL --out $O/sta_$TAG --clock-cal $CAL --cppr-lca \
  --count-align $CA --count-align-key region --clock-ocv table --clock-droop shared \
  --droop-regions $PF/droop_regions.json --hold-buffers HB4 --core-latency-ff 202.5 --clock-cell inv $CV --core-insertion view \
  > $O/sta_$TAG.log 2>&1; echo STA_${TAG}_RC $? $(date)
