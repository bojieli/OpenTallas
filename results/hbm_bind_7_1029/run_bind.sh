#!/usr/bin/env bash
# HBM-BIND-7: strict bind of variant V (manifest $R/$V/asbuilt.json, netlist $R/$V/out/asbuilt.json) against PLAN,
# memory-capped user scope (no admission queue: a ~2-5 min diagnostic bind, as HBM-BIND-5/6 / DIE-HBM-19)
set -u
R=/srv/opentallas-scratch2/claude/hbm-bind-7-1029; W=/srv/opentallas-scratch2/claude/wt/hbm-bind-7-1029; V=${1:-c1}; PLAN=${2:-$R/plan/c_q0/die_plan.json}
systemd-run --user --scope -q -p MemoryMax=96G /usr/bin/time -v python3 $W/tools/die_plan/bind.py bind $PLAN --asbuilt $R/$V/asbuilt.json --out $R/$V/out --strict --mem 24 > $R/$V/bind.log 2>&1
rc=$?; echo $rc > $R/$V/bind.rc; exit $rc
