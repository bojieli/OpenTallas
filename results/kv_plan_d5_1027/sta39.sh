#!/bin/bash
# KV-PLAN-DELTA-5: related-pair die STA on hm_r26q5c 7a03069b, clock = q5c39 (c39 PG) continuous-mesh proof (KV-GRT-STALL combo + post chain), MC = own q5c, shared MAIN die_sta_related (origin/main 1907eb530)
R19=/srv/opentallas-scratch2/claude/clock-kv-r19-1027; R23=/srv/opentallas-scratch2/claude/clock-kv-r23-1027; M=/srv/opentallas-scratch2/claude/kv-plan-d5-1027
export PYTHONPATH=$R19/in/pylib:$M/main/tools/die_plan; cd $M; N=$1; shift; ulimit -v 32000000; mkdir -p sta
python3 $M/main/tools/die_plan/die_sta_related.py $M/clk/q5c39 --plan $M/q5c_pd/hm_r26q5c39.json --out sta/$N --clock-tool $M/main/tools/die_plan --core-view kv3_head_eighth_e1=/srv/opentallas-scratch2/claude/clock-kv-r16-1026/views/kv3_head_eighth_e1 --core-view kv3_head_eighth_e5=/srv/opentallas-scratch2/claude/clock-kv-r16-1026/views/kv3_head_eighth_e5 --clock-ocv table --mesh-signoff TT=$M/mc/q5c39_TT.json,FF=$M/mc/q5c39_FF.json --hold-buffers HB4 --core-latency-ff 202.5 "$@" > sta/$N.log 2>&1
echo "$N rc=$? $(date -Is)" > sta/$N.run
