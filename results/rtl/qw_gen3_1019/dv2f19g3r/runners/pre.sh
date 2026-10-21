#!/bin/bash
# QW-GEN3 phase 1 (dv2f19g3r): GEN -> reset_sync audit -> strict port bind (no physical work).  Phase 2 (local, git):
# netlist relay export + layer_compile of THIS die's schedule; phase 3: chain.sh with OT_RELAY_SCHEDULE.  PILOT_NOT_A_GATE.
S=/srv/opentallas-scratch/claude/qwen-split-compute/dv2f19g3r
echo "$(date '+%F %T %Z') pre start" >> $S/PILOT.log
bash $S/gen.sh; rc=$?; echo "$(date '+%F %T %Z') GEN rc=$rc $(grep -h -E 'LAND_LIST|LAND_CROSS|CLKRX_PORTS' $S/out.log | head -4 | cut -c1-400)" >> $S/PILOT.log
[ $rc -eq 0 ] || exit 4
cd $S/src || exit 9
python3 tools/qwen_split/reset_sync_contract.py --die-v ../out/case/die.v --sync ../out/case/reset_sync.json > $S/reset_sync_audit.txt 2>&1; echo "$(date '+%F %T %Z') reset_sync audit rc=$? $(tail -1 $S/reset_sync_audit.txt | cut -c1-300)" >> $S/PILOT.log
OT_PORT_BIND_STRAPS=$S/src/results/arch/qwen_split_compute_1014/q_slice_1017/straps_dv2f18mu.json bash tools/qwen_split/port_bind_compute.sh $S/out/case/die.v $S/pre_bind > $S/pre_bind.line 2>&1; pb=$?
echo "$(date '+%F %T %Z') pre strict port-bind rc=$pb $(cat $S/pre_bind.line | tr '\n' ' ' | cut -c1-900)" >> $S/PILOT.log
echo "PRE_DONE pb=$pb" > $S/PRE_DONE
