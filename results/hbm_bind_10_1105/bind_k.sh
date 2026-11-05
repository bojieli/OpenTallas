#!/bin/bash
# HBM-BIND-9: strict bind of plan dir $1 (die_plan.json from c_route8b) on main-RTL as-built t10, host Python under prlimit. usage: bind_k.sh KDIR TAG
set -u; K=$1; TAG=$2
W=/srv/opentallas-scratch2/claude/hbm-bind-6; M=/srv/opentallas-scratch2/claude/hbm-bind-9
PD=$M/${TAG}p; O=$M/g_$TAG; mkdir -p $PD $O
for f in $W/m89/cm/*; do n=$(basename $f); [ "$n" = die_plan.json ] && continue; [ "$n" = g0 ] && continue; [ "$n" = g0.log ] && continue; [ -e $PD/$n ] || ln -s "$(readlink -f $f)" $PD/$n; done
rm -f $PD/die_plan.json; ln $K/die_plan.json $PD/die_plan.json
ln -f $W/g_t10/asbuilt.json $O/asbuilt.json; ln -f $W/g_t10/asbuilt_sources.json $O/asbuilt_sources.json
cd $W/tip2; export PYTHONDONTWRITEBYTECODE=1
/usr/bin/time -v prlimit --as=120000000000 python3 -I tools/die_plan/bind.py bind $PD/die_plan.json --asbuilt physical/die_plan/hbm/bind/d44v/asbuilt_t10.json --out $O --strict --all-gaps --mem 48 > $M/g_$TAG.bind.log 2>&1
echo "RC $? $(date)" > $M/g_$TAG.rc
