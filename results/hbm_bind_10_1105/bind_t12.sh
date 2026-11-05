#!/bin/bash
M=/srv/opentallas-scratch2/claude/hbm-bind-9; G=$M/g_t12m79f; rm -rf $G; mkdir -p $G
cp -al $M/e_t11/tj.json $G/asbuilt.json; cp -al $M/e_t11/out/asbuilt_sources.json $G/
cd /srv/opentallas-scratch2/claude/hbm-bind-6/tip2; export PYTHONDONTWRITEBYTECODE=1
/usr/bin/time -v prlimit --as=120000000000 python3 -I tools/die_plan/bind.py bind $M/m79fp/die_plan.json --asbuilt physical/die_plan/hbm/bind/d44v/asbuilt_t12.json --out $G --strict --all-gaps --mem 48 > $M/g_t12m79f.bind.log 2>&1; echo RC $? $(date) > $M/g_t12m79f.rc
