#!/usr/bin/env bash
set -u
python3 /srv/opentallas-scratch2/claude/wt/hbm-bind-5-1029/tools/die_plan/bind.py elab /srv/opentallas-scratch2/claude/hbm-bind-3-1029/plan0/die_plan.json --asbuilt /srv/opentallas-scratch2/claude/hbm-bind-5-1029/e2/asbuilt.json --out /srv/opentallas-scratch2/claude/hbm-bind-5-1029/e2/out --mem 24 > /srv/opentallas-scratch2/claude/hbm-bind-5-1029/e2/elab.log 2>&1
rc=$?; echo $rc > /srv/opentallas-scratch2/claude/hbm-bind-5-1029/e2/elab.rc; exit $rc
