#!/usr/bin/env bash
# DIE-HBM-28 strict all-gap bind (DIE-HBM-25 form; tools = wt/die-hbm-27 @ origin/main)
set -u; R=/srv/opentallas-scratch2/claude/die-hbm-30; W=/srv/opentallas-scratch2/claude/wt/die-hbm-27; V=$1; PLAN=$2; shift 2
systemd-run --user --scope -q -p MemoryMax=64G /usr/bin/time -v python3 $W/tools/die_plan/bind.py bind $PLAN --asbuilt $R/$V/asbuilt.json --out $R/$V/out --strict --all-gaps --mem 24 "$@" > $R/$V/bind.log 2>&1
echo $? > $R/$V/bind.rc
