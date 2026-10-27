#!/bin/bash
set -u
W=/srv/opentallas-scratch2/claude/wt/path-hbm-hubnw-1025
cd /srv/opentallas-scratch2/claude/path-hbm/hubnw2_1025/plan
python3 $W/tools/die_plan/check.py die_plan.json --out gates/g0 > gates-g0.log 2>&1; echo $? > gates-g0.exit
python3 $W/tools/die_plan/check.py die_plan.json --completeness --out gates/g0c > gates-g0c.log 2>&1; echo $? > gates-g0c.exit
