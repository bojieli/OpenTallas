#!/bin/bash
# FALLBACK-S81-2 10-26: G=2 re-price with no early core taps (COORD ruling 17:49): --core land (+3 per legacy-core lane
# endpoint) and --core rebuild (12.3 latency, std class); face + fwd FT readings. Light python, run from the worktree root.
set -euo pipefail
PLAN=${PLAN:-/srv/opentallas-scratch2/claude/path-s81-taps-1026/src/physical/die_plan/s81/die_plan_phyfit_g0fix.json}
O=${O:-results/fallback_s81_2_1026}
mkdir -p $O/regions $O/price
for core in land rebuild; do
  D=$O/regions/class_g2_$core
  python3 tools/die_plan/fallback_regions.py plan $PLAN --lat physical/die_plan/s81/lat/s81_latency.json --out $D --mode class --block 2 --core $core > $D.log
  for m in face fwd; do
    python3 tools/s81_dv/tokfunc/compose_tok_ds.py --lat $D/lat_$m.json --out $O/price/g2_${core}_$m > $O/price/g2_${core}_$m.log 2>&1 &
  done
done
wait
