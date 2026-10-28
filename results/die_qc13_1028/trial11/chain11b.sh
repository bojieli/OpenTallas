#!/bin/bash
set -e
cd /srv/opentallas-scratch2/claude/die-qc13-1028
python3 overlay11.py > overlay11.log 2>&1; echo "overlay rc $? $(date)" >> chain11.status
bash run_clock11.sh TT > grt11_TT.log 2>&1 & bash run_clock11.sh FF > grt11_FF.log 2>&1 & wait; echo "grt done $(date)" >> chain11.status
python3 -I /srv/opentallas-scratch2/claude/die-qc11-1028/duty_eval.py c11_TT/arr_TT.txt c11_FF/arr_FF.txt duty_trial11.json > duty11.log 2>&1; echo "duty rc $?" >> chain11.status
python3 eval11.py > eval11.log 2>&1; echo "eval rc $?" >> chain11.status
python3 render11.py > render11.log 2>&1; echo "render rc $?" >> chain11.status
bash ca/runCA11.sh > ca/runCA11.out 2>&1; echo "ca rc $? $(date)" >> chain11.status
