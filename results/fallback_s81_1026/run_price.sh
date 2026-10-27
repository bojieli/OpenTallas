#!/bin/bash
# FALLBACK-S81 10-26: region partitions x FT reading -> landed table + compose_tok_ds price (light python, run from the worktree root)
set -euo pipefail
PLAN=${PLAN:-/srv/opentallas-scratch2/claude/path-s81-taps-1026/src/physical/die_plan/s81/die_plan_phyfit_g0fix.json}
O=${O:-results/fallback_s81_1026}
python3 tools/s81_dv/tokfunc/compose_tok_ds.py --out $O/price/base > $O/price/base.log 2>&1
for cfg in 'partition 0' 'class 2' 'class 4'; do set -- $cfg
  D=$O/regions/$1_g$2
  python3 tools/die_plan/fallback_regions.py plan $PLAN --lat physical/die_plan/s81/lat/s81_latency.json --out $D --mode $1 --block $2 > $D.log
  for m in face fwd; do
    python3 tools/s81_dv/tokfunc/compose_tok_ds.py --lat $D/lat_$m.json --out $O/price/$1_g$2_$m > $O/price/$1_g$2_$m.log 2>&1 &
  done
done
wait
