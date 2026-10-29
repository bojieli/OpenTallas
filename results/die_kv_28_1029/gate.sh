#!/bin/bash
# DIE-KV-28: DIE-KV-27 gate.sh on MAIN 7a77f0bc6 (+81f9c6c39e FLOW-HOLD-1 12.19 real-view hold judgement), same inputs
# DIE-KV-27 (copy of DIE-KV-26 gate.sh, main tools e256f6799c): DIE-KV-22 gate.sh recipe on MAIN 2b90210bd die_sta_related, 4 signed views (e1/e2/e5/e6 @3e7fccd216), plan event26
set -u; TAG=$1; PF=$2; CA=$3; CAL=$4
O=/srv/opentallas-scratch2/claude/die-kv-28-1029; S=/srv/opentallas-scratch2/claude/wt/die-kv-28/tools/die_plan
PL=${PL:-/srv/opentallas-scratch2/claude/die-kv-26-1029/plan_e26a.json}
CV=""; for n in 1 2 5 6; do M=kv3_head_eighth_e$n; CV="$CV --core-view $M=/srv/opentallas-scratch2/claude/autopilot/closed/qwen_kvsys/${M}__3e7fccd216/view/$M"; done
mkdir -p $O/sta_$TAG; cp -r /srv/opentallas-scratch2/claude/die-kv-6-1028/sta_region/regchar $O/sta_$TAG/ 2>/dev/null
python3 $S/die_sta_related.py $PF --plan $PL --out $O/sta_$TAG --clock-cal $CAL --cppr-lca \
  --count-align $CA --count-align-key region --clock-ocv table --clock-droop shared \
  --droop-regions $PF/droop_regions.json --hold-buffers HB4 --core-latency-ff 202.5 --clock-cell inv $CV --core-insertion view \
  > $O/sta_$TAG.log 2>&1; echo STA_${TAG}_RC $? $(date)
