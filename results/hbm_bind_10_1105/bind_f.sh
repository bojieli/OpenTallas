#!/bin/bash
# HBM-BIND-10: strict binds (as-built t11) + G0 of k13f (C form on p7, stale hard-core ops dropped) and m79f (same on main 79e52bd).
set -u
M=/srv/opentallas-scratch2/claude/hbm-bind-9; W=/srv/opentallas-scratch2/claude/hbm-bind-6
export PYTHONDONTWRITEBYTECODE=1
for X in k13f m79f; do
  S=$M/k13p; [ $X = m79f ] && S=$M/m79c
  P=$M/${X}p; rm -rf $P; mkdir -p $P
  for f in $S/*; do n=$(basename $f); [ $n = die_plan.json ] && continue; ln -s "$(readlink -f $f)" $P/$n; done
  [ $X = m79f ] && { rm $P/cores; cp -a $M/m79c/cores $P/cores; }
  ln $M/$X.json $P/die_plan.json
  G=$M/g_t11$X; rm -rf $G; mkdir -p $G $M/${X}_g0
  cp -al $M/e_t11/tj.json $G/asbuilt.json; cp -al $M/e_t11/out/asbuilt_sources.json $G/
  ( cd $W/tip2; PYTHONPATH=tools/die_plan:tools/autopilot prlimit --as=48000000000 timeout 1500 python3 tools/die_plan/check.py $P/die_plan.json --out $M/${X}_g0 --core-conns $P/core_conns.json --core-macros $P/core_macros.json --plan-geom off > $M/${X}_g0.log 2>&1; echo G0 rc $? >> $M/${X}_g0.log ) &
  ( cd $W/tip2; /usr/bin/time -v prlimit --as=120000000000 python3 -I tools/die_plan/bind.py bind $P/die_plan.json --asbuilt physical/die_plan/hbm/bind/d44v/asbuilt_t11.json --out $G --strict --all-gaps --mem 48 > $M/g_t11$X.bind.log 2>&1; echo RC $? $(date) > $M/g_t11$X.rc ) &
done
wait
