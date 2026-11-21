#!/bin/bash
# FABLE-FIX-KV-HUB-R3: R8 table refresh (kv-plan-r3/d27c/r8_refresh_d27d.sh form) on a private tree after R8_STALE, then strict bind.
# usage: chain_r8_r3.sh TREE LAUNCH BINDOUT
set -uo pipefail
T=$1; L=$2; O=$3; W=/srv/opentallas-scratch2/claude/fable-fix-kv-hub; P=physical/die_plan/qwen_kvsys/plan_of_record
A=$W/r3/r8/$(basename $T); mkdir -p $A
export PYTHONDONTWRITEBYTECODE=1 OT_HCPARAM_ALL=1 OT_KV_HEAD_KST=2 OT_BIND_PLAN_PACKAGE=off
cd $T
chmod u+w $P/inputs
n=0; while IFS= read -r -d '' f; do cp -p "$f" "$f.r3p" && mv "$f.r3p" "$f"; n=$((n+1)); done < <(find $P/inputs $P/r8_ev.json -maxdepth 1 -type f -links +1 -print0)
echo PRIVATISED $n
cp -a $P/r8_ev.json $A/r8_ev.pre_refresh.json
cp -a $P/bind_of_record/bus_groups.json $A/bus_groups.bind.json
ls -la --time-style=long-iso $P/bind_of_record/bus_groups.json
python3 -I -B /srv/opentallas-scratch2/claude/rt/current/tools/die_plan/r8_refresh.py $P/plan_c.json $A/bus_groups.bind.json $P/r8_ev.json --asbuilt $P/asbuilt_vN.json --root $T > $A/r8_refresh.log 2>&1; r=$?
chmod a-w $P/inputs
echo R8_REFRESH_RC $r $(tail -2 $A/r8_refresh.log | cut -c1-400)
sha256sum $P/r8_ev.json | cut -c1-12
[ $r = 0 ] || exit $r
exec bash $W/r3/bind_gate_r3b.sh $L $O
