#!/bin/bash
set -u
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
W=/srv/opentallas-scratch2/claude/wt/die-qc-46; B=/srv/opentallas-scratch2/claude/die-qc-46
cd $W
python3 -I tools/die_plan/bind.py bind $B/plan/plan_qc45.json --asbuilt $W/results/qc_die33_1029/bind/final_asbuilt.json --out $B/bind45/out --strict > $B/bind45/bind.log 2>&1
echo "rc=$? $(date)" > $B/bind45/rc.txt
