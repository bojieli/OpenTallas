#!/bin/bash
# sta.sh NAME [extra die_sta_related args]  (CLOCK-KV-R19, intel1; real views e1/e5; shared die_sta_related from the R19 worktree = R18 tool + R19 opt-ins)
R=/srv/opentallas-scratch2/claude/clock-kv-r19-1027; T=/srv/opentallas-scratch2/claude/wt/clock-kv-r19/tools/die_plan
B=${B:-$R/r18}; P=${P:-$R/in/hm_r12.json}; V=/srv/opentallas-scratch2/claude/clock-kv-r16-1026/views
export PYTHONPATH=$R/in/pylib:$T; cd $R; N=$1; shift; ulimit -v 32000000
python3 $T/die_sta_related.py $B --plan $P --out sta/$N --clock-tool $T \
  --core-view kv3_head_eighth_e1=$V/kv3_head_eighth_e1 --core-view kv3_head_eighth_e5=$V/kv3_head_eighth_e5 "$@" > sta/$N.log 2>&1
echo "$N rc=$?" | tee sta/$N.run
