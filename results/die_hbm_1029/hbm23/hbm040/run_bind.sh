#!/usr/bin/env bash
# DIE-HBM-23 strict bind (HBM-BIND-9 run_bind.sh form; tools = wt/die-hbm-23 = hub main 92f899057c3)
set -u; R=/srv/opentallas-scratch2/claude/die-hbm-23; W=/srv/opentallas-scratch2/claude/wt/die-hbm-23; V=${1:-b2}; PLAN=$2
systemd-run --user --scope -q -p MemoryMax=64G /usr/bin/time -v python3 $W/tools/die_plan/bind.py bind $PLAN --asbuilt $R/$V/asbuilt.json --out $R/$V/out --strict --mem 24 > $R/$V/bind.log 2>&1
echo $? > $R/$V/bind.rc
