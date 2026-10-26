#!/usr/bin/env bash
# PLAN-DELTA/KV 10-25: KV die plan v3.9 (main) -> v3.9pd (TYPE-REDUCE KV, non-path types only).
#   usage: run_delta_kv.sh OUTDIR [base]
#   base : reproduce the v3.9 R8 chain on the unchanged plan (sanity: landing == committed r8/qwen_kvsys_r8_landing.json)
#   else : delta_kv.py in place on physical/die_plan/qwen_kvsys/{die_plan,core_conns,cells_evidence}.json, gen.py latency,
#          R8 chain with r8_row_publish.py over the merged hg row type (per-row latency published instead of R8 pads),
#          row_latency.py -> lat_v39pd/row_latency.json, reset offsets, G0 / G0C (+png).
set -euo pipefail
K=$(cd "$(dirname "$0")" && pwd); R=$(cd "$K/../../.." && pwd); T="$R/tools/die_plan"; D="$R/physical/die_plan/qwen_kvsys"
O=${1:?outdir}; MODE=${2:-delta}; mkdir -p "$O"
FAMILY=kv3_hg_v1_r2      # merged rows 1-6 only: kv3_hg (row 0, PATH) and kv3_hg_v3 (row 7) keep their type-level R8
BASE=3947653943           # main with plan v3.9: the before landing table for row_latency.py
OLD_LANDING="$O/landing_v39.json"; git -C "$R" show "$BASE:physical/die_plan/qwen_kvsys/r8/qwen_kvsys_r8_landing.json" > "$OLD_LANDING"
if [ "$MODE" = base ]; then P="$O/die_plan.json"; cp "$D/die_plan.json" "$P"
else P="$D/die_plan.json"; python3 "$K/delta_kv.py" "$P" --report "$O/delta_kv.json"; fi
python3 "$T/gen.py" latency "$P" --inplace --out "$O/lat"
mkdir -p "$O/r8"; cp "$D"/r8/*.py "$O/r8/"
gzip -dc "$D/r8/kv44_bus_groups.json.gz" > "$O/r8/bg_kv44.json"
python3 "$D/r8/r8_fault_exempt.py" "$O/r8/bg_kv44.json" "$O/r8/bg_fx.json"
python3 "$D/r8/r8_invariant_split.py" "$P" "$O/r8/bg_fx.json" "$O/r8/bg_split.json"
if [ "$MODE" = base ]; then cp "$O/r8/bg_split.json" "$O/r8/bg_pub.json"
else python3 "$K/r8_row_publish.py" "$P" "$O/r8/bg_split.json" "$O/r8/bg_pub.json" --family "$FAMILY"; fi
python3 "$D/r8/r8_rebase.py" "$P" "$O/r8/bg_pub.json" "$D/r8/kv44_bind_latency.json.gz" "$O/r8/bus_groups.json"
rm "$O/r8/bg_kv44.json" "$O/r8/bg_fx.json" "$O/r8/bg_split.json" "$O/r8/bg_pub.json"
python3 "$T/gen.py" latency "$P" --inplace --out "$O/lat" --groups "$O/r8/bus_groups.json" --bus leaf --replica type --fold-r8
python3 "$K/row_latency.py" "$OLD_LANDING" "$O/lat/qwen_kvsys_r8_landing.json" "$P" --out "$O/row_latency.json"
L="$O/lat/qwen_kvsys_r8_landing.json"
if [ "$MODE" != base ]; then      # install: R8 bus groups + landing next to the plan (check.py reads PLANDIR/r8), lat_v39pd/
  cp "$O/r8/bus_groups.json" "$L" "$D/r8/"; L="$D/r8/qwen_kvsys_r8_landing.json"
  mkdir -p "$D/lat_v39pd"; cp "$O/lat/qwen_kvsys_lat_pkg.sv" "$O/lat/qwen_kvsys_latency.json" "$O/row_latency.json" "$D/lat_v39pd/"
  python3 "$T/reset_tree.py" offsets "$P" --out "$O/reset_offsets.json" > /dev/null
fi
python3 "$T/check.py" "$P" --landing "$L" --out "$O/g0" --png > "$O/g0.log" 2>&1 || true
python3 "$T/check.py" "$P" --completeness --landing "$L" --out "$O/g0c" > "$O/g0c.log" 2>&1 || true
grep -hE "^G0C? (PASS|FAIL)" "$O/g0.log" "$O/g0c.log"
