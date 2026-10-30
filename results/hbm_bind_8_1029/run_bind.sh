#!/usr/bin/env bash
# HBM-BIND-8: strict bind of variant V against plan P (bind step only, elab hard-linked from die-hbm-19 d4)
set -u; R=/srv/opentallas-scratch2/claude/hbm-bind-8-1029; W=/srv/opentallas-scratch2/claude/wt/hbm-bind-8-1029; V=$1; PLAN=$2
python3 $W/tools/die_plan/bind.py bind $PLAN --asbuilt $R/$V/asbuilt.json --out $R/$V/out --strict --mem 24 > $R/$V/bind.log 2>&1
rc=$?; echo $rc > $R/$V/bind.rc; exit $rc
