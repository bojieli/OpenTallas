#!/bin/bash
# Q-DIEPLAN6 10-17 dv2f9: die chain (bind real views -> PDN r8 -> GRT -> STA tt/ff/ss) WITHOUT die repeaters
# (OT_DIE_REPAIR=0; tools/die_repeaters from main 267a32257 is in src for the repeater case). Strict bind gate on the
# plan's own straps (straps_dv2f8.json): PASS 0/0/0, so no diagnostic flag.
S=/srv/opentallas-scratch/claude/qwen-split-compute/dv2f9
cd $S/src || exit 9
grep -q "^rc=0" $S/out.log || { echo "GEN not rc=0" > $S/CHAIN_SKIPPED; exit 7; }
OT_PORT_BIND_STRAPS=$S/src/results/arch/qwen_split_compute_1014/q_slice_1017/straps_dv2f8.json OT_DIE_REPAIR=0 \
  OT_HOLD_BUDGET=die OT_SPLIT_PHY_NFACE=1 OT_ASSUMED_PHY_PG_ACCESS=1 bash tools/qwen_split/chain_after_build.sh dv2f9 > $S/chain.log 2>&1
echo "chain rc=$?" >> $S/chain.log
