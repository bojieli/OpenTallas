#!/bin/bash
# TOK-DS3 10-25 diagnostic probe: strict bind of CURRENT main plan (6a6fc12dd: adopt178 + faultfeed + attnh 2133 b) on asb/asbuilt_b178.json,
# tool = claude/tok-ds-bind178b-1025@29545922a (main merged; synced copy). Confirms which bind178 errors remain on main.
set -uo pipefail
R=/srv/opentallas-scratch2/claude/tok-ds/bind178; W=/srv/opentallas-scratch2/claude/wt/tok-ds-bind178; PLAN=$W/physical/die_plan/s81/die_plan.json; OUT=$R/out_main6a6
cd $W
python3 tools/die_plan/bind.py elab $PLAN --asbuilt $R/asb/asbuilt_b178.json --out $OUT --mem 16 > $R/elab_main6a6.log 2>&1; echo "elab rc=$?"
python3 tools/die_plan/bind.py bind $PLAN --asbuilt $R/asb/asbuilt_b178.json --out $OUT --strict > $R/bind_main6a6.log 2>&1; echo "bind rc=$?"
python3 tools/die_plan/bind.py portbind $PLAN --asbuilt $R/asb/asbuilt_b178.json --out $OUT > $R/portbind_main6a6.log 2>&1; echo "portbind rc=$?"
