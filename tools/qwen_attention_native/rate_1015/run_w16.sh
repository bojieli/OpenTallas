#!/bin/bash
# run_w16.sh BUILD NAME VEC CTX CAL MODE DMUT: one run of the w16 production binary (vectors = zfix set)
set -u
B=$1/parent$7/Vtb_qwen_tp8_attention_native_service_w16; O=$1/runs/$2; mkdir -p $O
$B +VEC=/srv/opentallas-scratch/claude/q-vmwb/zfix/vec/$3 +CTX=$4 +MODE=$6 +CAL=$5 > $O/native.log 2>&1; echo $? > $O/exit
grep '^{' $O/native.log | sed "s/^/$2 /"
