#!/usr/bin/env bash
# DIE-HBM-19: strict bind of variant V against plan P
set -u
R=/srv/opentallas-scratch2/claude/die-hbm-19/bind; W=/srv/opentallas-scratch2/claude/wt/die-hbm-19; V=${1}; PLAN=${2}
python3 $W/tools/die_plan/bind.py bind $PLAN --asbuilt $R/$V/asbuilt.json --out $R/$V/out --strict --mem 24 > $R/$V/bind.log 2>&1
rc=$?; echo $rc > $R/$V/bind.rc; exit $rc
