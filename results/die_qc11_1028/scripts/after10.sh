#!/bin/bash
# DIE-QC-11: after chain10 (trial10 = inv2 even-leg inverter tree) -> duty/MPW readout, spread, render, CA with START-TREE-1 + die STA
Q=/srv/opentallas-scratch2/claude/die-qc11-1028; cd $Q
while pgrep -f "bash chain10.sh" >/dev/null; do sleep 30; done
echo "chain10 ended $(date)" >> after10.status
python3 -I duty_eval.py c10_TT/arr_TT.txt c10_FF/arr_FF.txt duty/duty_trial10.json > duty10.log 2>&1; echo "duty rc $?" >> after10.status
python3 eval10.py > eval10.log 2>&1; echo "eval rc $?" >> after10.status
python3 render10.py > render10.log 2>&1; echo "render rc $?" >> after10.status
bash ca/runCA10.sh > ca/runCA10.out 2>&1; echo "ca rc $? $(date)" >> after10.status
