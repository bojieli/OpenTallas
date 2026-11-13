#!/bin/bash
# g0.sh PLANFILE(in physical/die_plan/s81) TAG [--completeness]
cd /srv/opentallas-scratch3/claude/wt/frame-forms-1; export PYTHONDONTWRITEBYTECODE=1; V=/srv/opentallas-scratch3/claude/frame-forms-1/vol
mkdir -p $V/$2; nice -n 5 python3 -I -B tools/die_plan/check.py physical/die_plan/s81/$1 --out $V/$2 --quiet $3 > $V/$2.log 2>&1; echo RC=$? >> $V/$2.log
