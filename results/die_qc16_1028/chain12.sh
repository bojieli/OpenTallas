#!/bin/bash
cd /srv/opentallas-scratch2/claude/die-qc16-1028
bash bays12.sh > bays12.log 2>&1; echo "bays rc $? $(date)" >> chain12.status
python3 overlay12.py > overlay12.log 2>&1; echo "overlay rc $? $(date)" >> chain12.status
bash run_clock12.sh TT > grt12_TT.log 2>&1 & bash run_clock12.sh FF > grt12_FF.log 2>&1 & wait; echo "grt done $(date)" >> chain12.status
python3 -I /srv/opentallas-scratch2/claude/die-qc11-1028/duty_eval.py c12_TT/arr_TT.txt c12_FF/arr_FF.txt duty_trial12.json > duty12.log 2>&1; echo "duty rc $?" >> chain12.status
python3 eval12.py > eval12.log 2>&1; echo "eval rc $?" >> chain12.status
python3 render12.py > render12.log 2>&1; echo "render rc $?" >> chain12.status
echo DONE >> chain12.status
