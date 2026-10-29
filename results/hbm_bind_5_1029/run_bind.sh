#!/usr/bin/env bash
# HBM-BIND-5: strict bind of variant V (manifest $R/$V/asbuilt.json; elab reused from HBM-BIND-4 b1 by hard link)
set -u
R=/srv/opentallas-scratch2/claude/hbm-bind-5-1029; W=/srv/opentallas-scratch2/claude/wt/hbm-bind-5-1029; V=${1:-c1}; PLAN=${2:-/srv/opentallas-scratch2/claude/hbm-bind-3-1029/plan0/die_plan.json}
mkdir -p $R/$V/out
[ -e $R/$V/out/asbuilt.json ] || ln /srv/opentallas-scratch2/claude/hbm-bind-4-1029/b1/out/asbuilt.json $R/$V/out/asbuilt.json
[ -e $R/$V/out/asbuilt_sources.json ] || cp /srv/opentallas-scratch2/claude/hbm-bind-4-1029/b1/out/asbuilt_sources.json $R/$V/out/
python3 $W/tools/die_plan/bind.py bind $PLAN --asbuilt $R/$V/asbuilt.json --out $R/$V/out --strict --mem 24 > $R/$V/bind.log 2>&1
rc=$?; echo $rc > $R/$V/bind.rc; head -1 $R/$V/bind.log; exit $rc
