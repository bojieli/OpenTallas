#!/bin/bash
# runz.sh NAME VEC CTX CAL MODE DMUT: one run of the zfix production binary (fix_r3 RL21/HXK8 + CTL Z-by-index)
set -u
Z=/srv/opentallas-scratch/claude/q-vmwb/zfix; B=$Z/parent$6/Vtb_qwen_tp8_attention_native_service
O=$Z/runs/$1; mkdir -p $O
$B +VEC=$Z/vec/$2 +CTX=$3 +MODE=$5 +CAL=$4 > $O/native.log 2>&1; echo $? > $O/exit
