#!/usr/bin/env bash
# HBM-BIND-13 strict bind (DIE-HBM-23 run_bind.sh form; tools = wt/hbm-bind-13 = 22e60875c07 (tools = hub main fbde5b15d98))
set -u; R=/srv/opentallas-scratch2/claude/hbm-bind-13-1029; W=/srv/opentallas-scratch2/claude/wt/hbm-bind-13; V=${1:-b2}; PLAN=$2
systemd-run --user --scope -q -p MemoryMax=64G /usr/bin/time -v python3 $W/tools/die_plan/bind.py bind $PLAN --asbuilt $R/$V/asbuilt.json --out $R/$V/out --strict --mem 24 > $R/$V/bind.log 2>&1
echo $? > $R/$V/bind.rc
