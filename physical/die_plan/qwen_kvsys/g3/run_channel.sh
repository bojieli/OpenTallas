#!/usr/bin/env bash
# Replay a channel-only FT geometry proposal from an existing KV plan.
# The result stays a candidate until G1/G2 and token-price acceptance.
set -euo pipefail
D=$(cd "$(dirname "$0")/.." && pwd)
R=$(cd "$D/../../.." && pwd)
T=$R/tools/die_plan
IN=${1:?input die_plan.json}; OUT=${2:?new candidate output directory}
mkdir -p "$OUT"
python3 "$D/g3/channel_paths.py" "$IN" "$OUT"
cp -r "$D/cores" "$D/census" "$D/core_conns.json" "$D/cells_evidence.json" "$D/die_io.json" "$D"/l1_cores_v3*.json "$OUT/"
python3 "$T/gen.py" latency "$OUT/die_plan.json" --inplace --out "$OUT/lat_natural"
mkdir -p "$OUT/r8"
gzip -dc "$D/r8/kv44_bus_groups.json.gz" > "$OUT/r8/bg_kv44.json"
python3 "$D/r8/r8_fault_exempt.py" "$OUT/r8/bg_kv44.json" "$OUT/r8/bg_fx.json"
python3 "$D/r8/r8_invariant_split.py" "$OUT/die_plan.json" "$OUT/r8/bg_fx.json" "$OUT/r8/bg_split.json"
python3 "$D/r8/r8_rebase.py" "$OUT/die_plan.json" "$OUT/r8/bg_split.json" "$D/r8/kv44_bind_latency.json.gz" "$OUT/r8/bus_groups.json"
python3 "$T/gen.py" latency "$OUT/die_plan.json" --inplace --out "$OUT/lat" --groups "$OUT/r8/bus_groups.json" --bus leaf --replica type --fold-r8
python3 "$D/lat_delta_v39.py" "$IN" "$OUT/die_plan.json" "$OUT/lat_delta_channel.json" "$OUT/lat/qwen_kvsys_latency.json"
python3 "$T/check.py" "$OUT/die_plan.json" --completeness --groups "$OUT/r8/bus_groups.json" --landing "$OUT/lat/qwen_kvsys_r8_landing.json" --out "$OUT/g0c"
