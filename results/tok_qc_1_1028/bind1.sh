#!/bin/bash
# TOK-QC-1 bind1: elab + strict bind + verify of the ONE-QC RTL on the count-aligned event (run via ot-run, cwd = repo)
set -u; W=$(pwd); O=$1; mkdir -p $O
P=results/tok_qc_1_1028/event/plan.json; A=physical/die_plan/qwen_compute/bind/asbuilt_tokqc1_ca.json
[ -s $O/asbuilt.json ] || python3 tools/die_plan/bind.py elab $P --asbuilt $A --out $O --mem 64 > $O/elab.log 2>&1; echo "elab rc $? $(date)" >> $O/status
python3 tools/die_plan/bind.py bind $P --asbuilt $A --out $O --strict > $O/bind.log 2>&1; echo "bind rc $? $(date)" >> $O/status
python3 tools/die_plan/bind.py verify $P --asbuilt $A --out $O --mem 64 > $O/verify.log 2>&1; echo "verify rc $? $(date)" >> $O/status
python3 tools/die_plan/bind.py portbind $P --asbuilt $A --out $O > $O/portbind.log 2>&1; echo "portbind rc $? $(date)" >> $O/status
