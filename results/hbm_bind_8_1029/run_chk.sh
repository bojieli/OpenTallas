#!/usr/bin/env bash
set -u; R=/srv/opentallas-scratch2/claude/hbm-bind-8-1029; W=/srv/opentallas-scratch2/claude/wt/hbm-bind-8-1029; N=$1; PLAN=$2; shift 2
python3 $W/tools/die_plan/check.py $PLAN --out $R/chk/$N "$@" > $R/chk/$N.log 2>&1; rc=$?; echo $rc > $R/chk/$N.rc; exit $rc
