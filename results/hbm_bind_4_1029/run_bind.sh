#!/usr/bin/env bash
set -u
R=/srv/opentallas-scratch2/claude/hbm-bind-4-1029; W=/srv/opentallas-scratch2/claude/wt/hbm-bind-4-1029; V=${1:-b1}
python3 $W/tools/die_plan/bind.py bind /srv/opentallas-scratch2/claude/hbm-bind-3-1029/plan0/die_plan.json --asbuilt $R/$V/asbuilt.json --out $R/$V/out --strict --mem 24 > $R/$V/bind.log 2>&1
rc=$?; echo $rc > $R/$V/bind.rc; head -1 $R/$V/bind.log; exit $rc
