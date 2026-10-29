#!/bin/bash
# TOK-QC-2: strict bind (+verify +portbind) of the ONE-QC RTL on the TOK-QC-2 event. usage: bind.sh OUT RECIPE [nover]
# elaboration reused from TOK-QC-1 bind1 (same netlist/RTL/recipe sources; asbuilt.json symlinked into OUT)
set -u; O=$1; A=$2; mkdir -p $O
P=results/tok_qc_2_1028/event/plan.json
[ -e $O/asbuilt.json ] || python3 tools/die_plan/bind.py elab $P --asbuilt $A --out $O --mem 64 > $O/elab.log 2>&1
python3 tools/die_plan/bind.py bind $P --asbuilt $A --out $O --strict > $O/bind.log 2>&1; echo "bind rc $? $(date)" >> $O/status
[ "${3:-}" = nover ] && exit 0
python3 tools/die_plan/bind.py verify $P --asbuilt $A --out $O --mem 64 > $O/verify.log 2>&1; echo "verify rc $? $(date)" >> $O/status
python3 tools/die_plan/bind.py portbind $P --asbuilt $A --out $O > $O/portbind.log 2>&1; echo "portbind rc $? $(date)" >> $O/status
