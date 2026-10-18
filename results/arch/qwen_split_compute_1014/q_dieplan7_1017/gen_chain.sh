#!/bin/bash
# Q-DIEPLAN7 10-17 dv2f10: GEN (d2d_rom/ucie_kv MX) then the no-repeater chain (bind -> PDN r8 -> GRT -> STA)
S=/srv/opentallas-scratch/claude/qwen-split-compute/dv2f10
echo "$(date "+%F %T %Z") GEN start" > $S/status
bash $S/run.sh; rc=$?; echo "$(date "+%F %T %Z") GEN rc=$rc" >> $S/status
[ $rc -eq 0 ] || exit $rc
bash $S/chain_nr.sh; rc=$?; echo "$(date "+%F %T %Z") chain_nr rc=$rc (see chain.log, chain/STATUS.log)" >> $S/status
exit $rc
