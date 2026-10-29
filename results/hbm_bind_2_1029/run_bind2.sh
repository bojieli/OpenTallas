#!/usr/bin/env bash
# HBM-BIND-2 strict bind (bind step only; netlist c0eadd4c + manifest RTL set as HBM-BIND-1/Codex current_r2)
set -u; V=$1; R=/srv/opentallas-scratch2/claude/hbm-bind-2-1029
python3 /srv/opentallas-scratch2/claude/wt/hbm-bind-2-1029/tools/die_plan/bind.py bind ${PLAN:-/srv/opentallas-scratch2/claude/codex-hbm-bind-0300/plan/die_plan.json} --asbuilt $R/$V/asbuilt_b.json --out $R/$V/out --strict --mem 24 > $R/$V/bind.log 2>&1
rc=$?; echo $rc > $R/$V/bind.rc; exit $rc
