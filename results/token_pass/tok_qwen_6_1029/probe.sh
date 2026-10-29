#!/bin/bash
# TOK-QWEN-6 10-29: estimate-before-build HEAD reservation price. Same recipe as Codex native7_currentqc
# (bind7, KST 90,90,88,88,88,78,78, CST 5,5,5,6,4,4, F2, derived service pad) with OT_KV_HEAD_PREP_EDGES=$1.
W=/srv/opentallas-scratch2/claude/wt/tok-qwen-6
O=/srv/opentallas-scratch2/claude/tok-qwen-6-1029/hp/hp$1
rm -rf $O; mkdir -p $O
cd $W && CST=5,5,5,6,4,4 KST=90,90,88,88,88,78,78 OT_KV_HEAD_PREP_EDGES=$1 \
  bash physical/die_plan/qwen_kvsys/boot_v36/run_mu833.sh /srv/opentallas-scratch2/claude/die-kv-23-1028/bind7 $O > $O/run.out 2>&1
echo "rc=$?" >> $O/run.out
