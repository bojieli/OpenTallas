#!/bin/bash
set -eu
cd /srv/opentallas-scratch2/claude/wt/die-qc-51
P=physical/die_plan/qwen_compute/plan_of_record/plan_qc52.json
A=results/qc_die33_1029/bind/final_asbuilt.json
O=/srv/opentallas-scratch2/claude/die-qc-51/bind52
python3 tools/die_plan/bind.py elab $P --asbuilt $A --out $O --mem 32
python3 tools/die_plan/bind.py bind $P --asbuilt $A --out $O --strict
echo BIND52_DONE
