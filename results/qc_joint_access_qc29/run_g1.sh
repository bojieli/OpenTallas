#!/bin/bash
cd /srv/opentallas-scratch2/claude/die-qc29/main_src
for v in base grow; do python3 tools/die_plan/check.py /srv/opentallas-scratch2/claude/die-qc29/g1/plan_$v.json --out /srv/opentallas-scratch2/claude/die-qc29/g1/$v --png > /srv/opentallas-scratch2/claude/die-qc29/g1/$v/check.log 2>&1; echo "$v rc $?"; done
