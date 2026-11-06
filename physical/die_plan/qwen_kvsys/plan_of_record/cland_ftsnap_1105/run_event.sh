#!/bin/sh
# DIE-KV-80/PLAN 11-05 KV plan event CLAND-BAND + FT-SITE-OFFROW (COORD 19:37 (3a), (f)); repo root, on main 7305773106e.
#  1. cland_band_fit: bands a placed macro overlaps with macro-free area < 1.25 x ring reserve are re-sited (same size,
#     least shift, clear of all planning obstacles): kv3_hub_Eo monitor_0, kv3_hub_Wo monitor_0 + monitor_1.
#  2. ft_nudge --snap-only: explicit FT bit sites off the kit row/site grid snap as one block per station:
#     kv3_hgi_v8 ft27 st4 (523 bits), kv3_hub_Wi 6 stations (2682 bits); max move 0.148 um.
set -e
P=physical/die_plan/qwen_kvsys/plan_of_record
O=${1:-/tmp/kvev}; mkdir -p $O
git show 7305773106e:$P/plan_c.json > $O/plan_c.base.json
python3 tools/die_plan/cland_band_fit.py $O/plan_c.base.json $P/eW_sidecar.json $O/plan_c.band.json $O/band_report.json
python3 tools/die_plan/ft_nudge.py $O/plan_c.band.json $O/plan_c.ev.json $O/snap_ledger.json --snap-only
cmp $O/plan_c.ev.json $P/plan_c.json && echo "replay: plan_c.json identical"
