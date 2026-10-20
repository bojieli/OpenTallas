#!/bin/bash
# usage: run_probe2.sh NAME "ENV..." ARGS...
cd /srv/opentallas-scratch/claude/lh-reprice3/src || exit 9
n=$1; envs=$2; shift 2
O=/srv/opentallas-scratch/claude/hbm-rate-drop/out2; mkdir -p $O
env $envs PYTHONPATH=tools python3 /srv/opentallas-scratch/claude/hbm-rate-drop/probe2.py "$@" --only only_hbm_bw,only_att_qwen,all,info_banklat_all,rec,rec_lat,rec_att,rec_att_bigprog,all_bigprog --jobs 10 --out $O/$n.json > $O/$n.log 2>&1
echo "$n rc=$?"
