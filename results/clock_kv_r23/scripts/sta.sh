#!/bin/bash
# CLOCK-KV-R23 gate = R19..R22 gate args, MAIN 8810c5e6a tools (die_sta_related sha1 53e4d5fe = R22 branch), match-pins default ON, per-endpoint HB4
R19=/srv/opentallas-scratch2/claude/clock-kv-r19-1027; R=/srv/opentallas-scratch2/claude/clock-kv-r23-1027; export PYTHONPATH=$R19/in/pylib:$R/tools/die_plan; cd $R; N=$1; B=$2; MC=$3; shift 3; ulimit -v 32000000
python3 $R/tools/die_plan/die_sta_related.py $B --plan $R19/in/hm_r12.json --out sta/$N --clock-tool $R/tools/die_plan --core-view kv3_head_eighth_e1=/srv/opentallas-scratch2/claude/clock-kv-r16-1026/views/kv3_head_eighth_e1 --core-view kv3_head_eighth_e5=/srv/opentallas-scratch2/claude/clock-kv-r16-1026/views/kv3_head_eighth_e5 --clock-ocv table --mesh-signoff TT=${MC}_TT.json,FF=${MC}_FF.json --hold-buffers HB4 --core-latency-ff 202.5 "$@" > sta/$N.log 2>&1
echo "$N rc=$? $(date -Is)" > sta/$N.run
