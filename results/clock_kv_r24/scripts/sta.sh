#!/bin/bash
# CLOCK-KV-R24 gate = R23 args (r22u proof + own MC), plan hm_r24 (lattice+ft0, 12.2a1 core islands), die_sta_related with CONTENT pin match
R19=/srv/opentallas-scratch2/claude/clock-kv-r19-1027; R23=/srv/opentallas-scratch2/claude/clock-kv-r23-1027; R=/srv/opentallas-scratch2/claude/clock-kv-r24-1027; export PYTHONPATH=$R19/in/pylib:$R/tools/die_plan; cd $R; N=$1; PL=$2; shift 2; ulimit -v 32000000; mkdir -p sta
python3 $R/tools/die_plan/die_sta_related.py /srv/opentallas-scratch2/claude/clock-kv-r22-1027/r22u --plan $PL --out sta/$N --clock-tool $R/tools/die_plan --core-view kv3_head_eighth_e1=/srv/opentallas-scratch2/claude/clock-kv-r16-1026/views/kv3_head_eighth_e1 --core-view kv3_head_eighth_e5=/srv/opentallas-scratch2/claude/clock-kv-r16-1026/views/kv3_head_eighth_e5 --clock-ocv table --mesh-signoff TT=$R23/mc/r22u_TT.json,FF=$R23/mc/r22u_FF.json --hold-buffers HB4 --core-latency-ff 202.5 "$@" > sta/$N.log 2>&1
echo "$N rc=$? $(date -Is)" > sta/$N.run
