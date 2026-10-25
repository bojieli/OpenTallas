#!/usr/bin/env bash
# HBM-BIND (2026-10-24): regenerate the B2 bind delta from the plan's lane latency table (table-driven delays).
#   tools/hbm_b2/regen_b2.sh OUT [PLAN_LANES] [CENSUS_MAP]
#   defaults: results/arch/hbm_arch_1024/b2_delay_inputs/B2m_lanes.json / B2m_census_map.json (extract of the B2m plan).
#   When the plan changes (B2n ...): extract its lanes the same way and rerun; commit OUT/wiring.json as
#   results/arch/hbm_arch_1024/b2_bind_wiring.json and OUT/b2_delays.json as results/arch/hbm_arch_1024/b2_delays.json.
# Steps: wiring without delays -> B2 die top -> b2_delays.py (plan lanes on every cross-partition connection; d4g bank-
# latency rules; SEL_LAT; hub echo) -> wiring with delays.  Delay params never change connectivity, so one pass suffices.
set -euo pipefail
OUT=$(realpath -m "${1:?out}"); I=results/arch/hbm_arch_1024/b2_delay_inputs
PL=${2:-$I/B2m_lanes.json}; CM=${3:-$I/B2m_census_map.json}
DIE=physical/die_plan/hbm/bind/inputs/die_r18h5.v.gz; AB=physical/die_plan/hbm/bind/asbuilt.json
CEN=physical/die_plan/hbm/inputs/census/hbm_census.json.gz
mkdir -p "$OUT"
python3 tools/hbm_b2/make_wiring.py --die $DIE --asbuilt $AB --out "$OUT/wiring0.json" > "$OUT/mw0.log"
python3 tools/hbm_b2/b2_top.py --die $DIE --asbuilt $AB --delta "$OUT/wiring0.json" --out "$OUT/top0" > "$OUT/top0.log" 2>&1 || true
python3 tools/hbm_b2/b2_delays.py --die "$OUT/top0/die_b2.v" --plan "$PL" --census-map "$CM" \
  $( [ -f $CEN ] && echo --census $CEN ) --out "$OUT/b2_delays.json" | tee "$OUT/delays.log"
python3 tools/hbm_b2/make_wiring.py --die $DIE --asbuilt $AB --delays "$OUT/b2_delays.json" --out "$OUT/wiring.json" > "$OUT/mw.log"
echo "REGEN_B2 OK $OUT"
