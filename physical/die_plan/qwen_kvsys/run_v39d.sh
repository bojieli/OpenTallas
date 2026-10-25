#!/usr/bin/env bash
# KV-PLAN2 10-25: plan v3.9 -> v3.9d = geom_v39d.py (pv column +259.2, hub_Wi E-W channel, ectlk quarters) + v3.9c (face pins in channel mouths, per-bit ft station sites), see g3/chan_windows.py.
# Partitions, types, outlines, cores, lanes and buses are unchanged; only port windows move, ft slot regs_um are dropped
# (per-bit sites on each bit's route) and a slot's station count is raised where its new route needs it (405 um).
#   chan_windows.py -> gen.py latency -> R8 (kv44 groups rebased, as run_v39.sh) -> lat delta -> reset offsets -> G0/G0C
#   usage: run_v39c.sh V39_DIE_PLAN.json OUTDIR
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd); R=$(cd "$D/../../.." && pwd); T="$R/tools/die_plan"
IN=${1:?v3.9 die_plan.json}; O=${2:?output directory}; mkdir -p "$O"
mkdir -p "$O/cores"; cp -r "$D/cores/." "$O/cores/"
python3 "$D/g3/geom_v39d.py" "$IN" "$O/die_plan_geom.json" --cores-out "$O/cores"
cp "$D/core_conns.json" "$O/"
python3 "$D/g3/chan_windows.py" "$O/die_plan_geom.json" --report "$O/chan_windows.json" > "$O/die_plan.json"
python3 "$D/g3/core_reface.py" "$O/die_plan.json" --types kv3_hub_Wi
cp -r "$D/census" "$D/cells_evidence.json" "$D"/l1_cores_v3*.json "$O/"
python3 "$T/gen.py" latency "$O/die_plan.json" --inplace --out "$O/lat"
mkdir -p "$O/r8" && cp "$D"/r8/*.py "$O/r8/"
gzip -dc "$D/r8/kv44_bus_groups.json.gz" > "$O/r8/bg_kv44.json"
python3 "$D/r8/r8_fault_exempt.py" "$O/r8/bg_kv44.json" "$O/r8/bg_fx.json"
python3 "$D/r8/r8_invariant_split.py" "$O/die_plan.json" "$O/r8/bg_fx.json" "$O/r8/bg_split.json"
python3 "$D/r8/r8_rebase.py" "$O/die_plan.json" "$O/r8/bg_split.json" "$D/r8/kv44_bind_latency.json.gz" "$O/r8/bus_groups.json"
rm "$O/r8/bg_kv44.json" "$O/r8/bg_fx.json" "$O/r8/bg_split.json"
python3 "$T/gen.py" latency "$O/die_plan.json" --inplace --out "$O/lat" --groups "$O/r8/bus_groups.json" --bus leaf --replica type --fold-r8
cp "$O/lat/qwen_kvsys_r8_landing.json" "$O/r8/"
python3 "$D/lat_delta_v39.py" "$IN" "$O/die_plan.json" "$O/lat_delta_v39d.json" "$O/lat/qwen_kvsys_latency.json"
python3 "$T/reset_tree.py" offsets "$O/die_plan.json" --out "$O/reset_offsets.json" > /dev/null
python3 "$T/check.py" "$O/die_plan.json" --landing "$O/r8/qwen_kvsys_r8_landing.json" --out "$O/g0x" || true
python3 "$T/check.py" "$O/die_plan.json" --completeness --landing "$O/r8/qwen_kvsys_r8_landing.json" --out "$O/g0cx" || true
