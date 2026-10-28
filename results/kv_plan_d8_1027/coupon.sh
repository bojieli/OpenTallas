#!/bin/bash
# KV-PLAN-DELTA-8 F1 A/B coupon: ft_station_probe (bounded part, segmented, 50 it, signal max M7, .75 derate)
# A = legacy stacked M4+M5 station pins (--stacked-station-pins), B = F1 default. GRT via ot-run in docker.
PLAN=$1; PART=$2; O=$3; V=$4; shift 4
T=/srv/opentallas-scratch2/claude/wt/kv-plan-d8-1027/tools/die_plan
SL=(); for s in "$@"; do SL+=(--slot "$s"); done
X=(); [ "$V" = A ] && X=(--stacked-station-pins)
mkdir -p $O
python3 $T/ft_station_probe.py $PLAN --out $O --part $PART --segmented --iterations 50 --signal-max M7 "${X[@]}" "${SL[@]}" > $O.gen.log 2>&1 || { echo PROBEGEN_FAIL; tail -3 $O.gen.log; exit 1; }
~/.local/bin/ot-run --mem 24 --threads 8 --hosts localhost --dir $O -- docker run --rm --name d8-cpn-$(basename $O)-$$ --cpus 8 --memory 24g --memory-swap 24g -v $O:/work -w /work -e HUID=$(id -u) -e HGID=$(id -g) openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 8 -exit /work/grt/grt.tcl > /work/grt/route.log 2>&1; rc=\$?; chown -R \$HUID:\$HGID /work; exit \$rc" > $O.run.log 2>&1
echo COUPON_RC $? >> $O.run.log
grep -A12 "Final congestion report" $O/grt/route.log | tail -12
