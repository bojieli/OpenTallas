#!/usr/bin/env bash
# HBM-BIND-1 strict bind (bind step only; elab reused from Codex current_r2, same netlist c0eadd4c + manifest RTL set)
set -u; V=$1; R=/srv/opentallas-scratch2/claude/hbm-bind-1-1029
python3 /srv/opentallas-scratch2/claude/wt/hbm-bind-1-1029/tools/die_plan/bind.py bind /srv/opentallas-scratch2/claude/codex-hbm-bind-0300/plan/die_plan.json --asbuilt $R/$V/asbuilt_b.json --out $R/$V/out --strict --mem 24 > $R/$V/bind.log 2>&1
rc=$?; echo $rc > $R/$V/bind.rc; exit $rc
