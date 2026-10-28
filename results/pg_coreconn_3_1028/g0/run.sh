#!/bin/bash
W=/srv/opentallas-scratch2/claude/wt/pg-coreconn-3; O=/srv/opentallas-scratch2/claude/pg-coreconn-3/g0
PY=/srv/opentallas-scratch2/claude/venv-pytest-hb4/bin/python
cd $W
for d in s81 s81_head qwen_compute qwen_kvsys hbm; do
 for m in warn strict; do
  f=""; [ $m = strict ] && f=--strict-core-pg
  ( $PY tools/die_plan/check.py physical/die_plan/$d/die_plan.json --out $O/$d.$m --quiet $f > $O/$d.$m.log 2>&1; echo "rc=$?" >> $O/$d.$m.log ) &
 done
done
wait; echo ALLDONE $(date) > $O/done.txt
