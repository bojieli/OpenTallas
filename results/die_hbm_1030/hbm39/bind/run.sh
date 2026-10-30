#!/bin/bash
# strict bind of plan/$1 (d35c base vs d38s), same asbuilt as DIE-HBM-31/35 (die-hbm-31/b31t)
P=$1; mkdir -p /srv/opentallas-scratch2/claude/die-hbm-39/bind/$P; ulimit -v 30000000
python3 -u /srv/opentallas-scratch2/claude/wt/die-hbm-39/tools/die_plan/bind.py bind /srv/opentallas-scratch2/claude/die-hbm-39/plan/$P/die_plan.json --asbuilt /srv/opentallas-scratch2/claude/die-hbm-39/bind/asbuilt.json --out /srv/opentallas-scratch2/claude/die-hbm-39/bind/$P/out --strict --all-gaps --mem 24 > /srv/opentallas-scratch2/claude/die-hbm-39/bind/$P/bind.log 2>&1; echo $? > /srv/opentallas-scratch2/claude/die-hbm-39/bind/$P/bind.rc
