#!/bin/bash
# DIE-HBM-58/CLK: when the full-hub NE_v2 DRT (intel1 clkloc7-drt-NE_v2, NDR w0.12 + fat vias) ends, copy its route to
# epyc2, re-solve the NE matched mesh and re-run the 12.25 die gate (A feed, origin/main tools). Read-only on the DRT dir.
set -uo pipefail
S=/srv/opentallas-scratch2/claude/hbm-clkloc-7/drc/NE_v2; W=/home/ubuntu/scratch-root/claude/die-hbm-58-clk
L=/srv/opentallas-scratch2/claude/die-hbm-58-clk/nev2_chain.log
while ! ssh -o ControlPath=none intel1 "grep -q '^EXIT ' $S/drt.log"; do sleep 300; done
echo "DRT ended $(date)" >> $L; ssh -o ControlPath=none intel1 "tail -3 $S/drt.log; grep DRT-0199 $S/drt.log | tail -1; wc -l < $S/drc.rpt" >> $L 2>&1
ssh -o ControlPath=none intel1 "test -s $S/drt.spef" || { echo "NO SPEF (extraction died) -> needs recover from drt.def/odb" >> $L; exit 1; }
ssh -o ControlPath=none intel1 "cd $S && tar cf - pilot.def drt.spef drc.rpt" | ssh -o ControlPath=none epyc2 "mkdir -p $W/in/NE_v2 && tar xf - -C $W/in/NE_v2"
ssh -o ControlPath=none epyc2 "cd $W && ./matched_nev2.sh > matched_nev2.log 2>&1 && systemd-run --user --wait --unit=dhbm58-gate-nev2 -p MemoryMax=48G -p CPUQuota=400% -E DATA=$W/data_nev2 -E TAG=_nev2 $W/gate.sh A main && python3 summ.py gate_A_main_nev2 && python3 hubstat.py gate_A_main_nev2" >> $L 2>&1
echo "CHAIN_DONE $(date)" >> $L
