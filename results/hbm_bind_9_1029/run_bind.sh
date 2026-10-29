#!/usr/bin/env bash
# HBM-BIND-9: strict bind of variant V (manifest $R/$V/asbuilt.json, netlist $R/$V/out/asbuilt.json) against PLAN (HBM-BIND-7 form)
set -u
R=/srv/opentallas-scratch2/claude/hbm-bind-9-1029; W=/srv/opentallas-scratch2/claude/wt/hbm-bind-9; V=${1:-b0}; PLAN=${2:-$R/plan/d22a/die_plan.json}
systemd-run --user --scope -q -p MemoryMax=96G /usr/bin/time -v python3 $W/tools/die_plan/bind.py bind $PLAN --asbuilt $R/$V/asbuilt.json --out $R/$V/out --strict --mem 24 > $R/$V/bind.log 2>&1
rc=$?; echo $rc > $R/$V/bind.rc; exit $rc
