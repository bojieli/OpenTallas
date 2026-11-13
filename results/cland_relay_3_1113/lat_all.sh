#!/bin/bash
# CLAND-RELAY-3: lane_asbuilt_latency.py (branch tree = main's file) on one bind of record per die
cd /srv/opentallas-scratch2/claude/cland-relay-3/wt; O=/srv/opentallas-scratch2/claude/cland-relay-3/lat; mkdir -p $O
run() { n=$1; shift; python3 -I tools/die_plan/lane_asbuilt_latency.py "$@" --tsv $O/$n.tsv --json $O/$n.json > $O/$n.log 2>&1; echo "$n rc $?"; tail -3 $O/$n.log | cut -c1-400; }
run kv /srv/opentallas-scratch2/claude/kit-ops-1/kvbind_vN2i/out /srv/opentallas-scratch2/claude/kw45/src_kv_main_66e6607e3f/physical/die_plan/qwen_kvsys/plan_of_record/plan_c.json --asbuilt /srv/opentallas-scratch2/claude/kw45/src_kv_main_66e6607e3f/physical/die_plan/qwen_kvsys/plan_of_record/asbuilt_vN.json
run s81 /srv/opentallas-scratch2/claude/kit-ops-1/s81_r12bA/out_main_7073a6b4a5_b /srv/opentallas-scratch2/claude/kw45/src_s81_main_7073a6b4a5/physical/die_plan/s81/plan_h2_2249.json --asbuilt /srv/opentallas-scratch2/claude/kit-ops-1/s81_r12bA/asbuilt_kitops1_7073a6b4a5.json
