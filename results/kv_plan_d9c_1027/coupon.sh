#!/bin/bash
# DIE-KV-3/STATIONS FT coupon (KV-PLAN-DELTA-5/6 recipe: ft_station_probe bounded --segmented, 50 it, signal max M7, .75 derate)
# usage: coupon.sh PLAN PART OUTDIR [extra probe flags]
PLAN=$1; p=$2; O=$3; shift 3
W=/srv/opentallas-scratch2/claude/wt/kv-plan-d9b
export PYTHONPATH=$W/tools/die_plan:$W:/srv/opentallas-scratch2/claude/kv-plan-d5-1027/pylib
python3 $W/tools/die_plan/ft_station_probe.py $PLAN --out $O --part $p --segmented --iterations 50 --signal-max M7 "$@" > $O.gen.log 2>&1 || { echo PROBEGEN_FAIL; exit 1; }
docker run --rm --name kvst-$p-$(basename $O)-$$ --cpus 8 --memory 24g --memory-swap 24g -v $O:/work -w /work -e HUID=$(id -u) -e HGID=$(id -g) openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 8 -exit /work/grt/grt.tcl > /work/grt/route.log 2>&1; rc=\$?; chown -R \$HUID:\$HGID /work; exit \$rc"; echo COUPON_RC $?
