#!/usr/bin/env bash
# HBM-BIND-6: strict bind of variant V (manifest $R/$V/asbuilt.json, netlist $R/$V/out/asbuilt.json)
set -u
R=/srv/opentallas-scratch2/claude/hbm-bind-6-1029; W=/srv/opentallas-scratch2/claude/wt/hbm-bind-6-1029; V=${1:-c3}; PLAN=${2:-/srv/opentallas-scratch2/claude/hbm-bind-3-1029/plan0/die_plan.json}
python3 $W/tools/die_plan/bind.py bind $PLAN --asbuilt $R/$V/asbuilt.json --out $R/$V/out --strict --mem 24 > $R/$V/bind.log 2>&1
rc=$?; echo $rc > $R/$V/bind.rc; head -c 600 $R/$V/bind.log; exit $rc
