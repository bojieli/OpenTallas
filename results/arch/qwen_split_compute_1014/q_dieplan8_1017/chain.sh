#!/bin/bash
# Q-DIEPLAN8 10-17 dv2f11 die chain WITH die repeaters (OT_DIE_REPAIR=1, tools/die_repeaters = main 6f5039961):
# + OT_PDN_RELAY_GRIDS=1 (relay macros get the per-phase M8 macro grids; dv2f10 test: 498 relays PSM-0039).
# strict bind -> PDN r8 -> repeaters -> GRT -> STA tt/ff/ss.  Same flags as dv2f10 otherwise.
S=/srv/opentallas-scratch/claude/qwen-split-compute/dv2f11
cd $S/src || exit 9
grep -q "^rc=0" $S/out.log || { echo "GEN not rc=0" > $S/CHAIN_SKIPPED; exit 7; }
OT_PORT_BIND_STRAPS=$S/src/results/arch/qwen_split_compute_1014/q_slice_1017/straps_dv2f8.json OT_DIE_REPAIR=1 OT_PDN_RELAY_GRIDS=1 \
  OT_HOLD_BUDGET=die OT_SPLIT_PHY_NFACE=1 OT_SPLIT_PHY_TALL=1 OT_ASSUMED_PHY_PG_ACCESS=1 bash tools/qwen_split/chain_after_build.sh dv2f11 > $S/chain.log 2>&1
echo "chain rc=$?" >> $S/chain.log
