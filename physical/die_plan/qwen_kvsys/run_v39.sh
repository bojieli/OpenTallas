#!/usr/bin/env bash
# KV-405 10-24: plan v3.8x -> v3.9 (owner decisions 12 / 17, METHODOLOGY rulings 9.3 / 9.4: signals <= M7, every hop /
# ft station spacing / internal-station hop <= 405 um exactly, die.reach_um 405, no ft_reserved) =
#   post_v39.py (die budgets, ft slot station counts at 405 um on the G0 route and on the worst pin bit, internal-station
#   re-spacing + lane fixed_cycles, kv3_phy reset taps at the E face)
#   + g3/ft_channel_regs.py --add-stations --max-add 3 (core-free station sites at <= 405 um on the final counts)
#   + gen.py latency (lat_*) + r8.py pads (R8 landing table on the new latency) + G0 / G0C.
# Later plan moves (e.g. the v3.9ft crossing reduction) layer on top: run them on v3.8x first, then this chain.
# Core pins (qkd_ahub r2 outline + S-face clock entry, qkd_ectlk N-face centre clock entry): core_pins_v39.py PLAN_DIR
# first (in place, idempotent).  Reset offsets (wavefront): OUTDIR/reset_offsets.json.
#   usage: run_v39.sh V38X_DIE_PLAN.json OUTDIR [CODEX_REACH405_PLAN.json]
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd); R=$(cd "$D/../../.." && pwd); T="$R/tools/die_plan"
IN=${1:?v3.8x die_plan.json}; O=${2:?output directory}; CX=${3:-}; mkdir -p "$O"
python3 "$D/post_v39.py" "$IN" ${CX:+--codex "$CX"} --report "$O/post_v39.json" > "$O/die_plan.0.json"
python3 "$D/g3/ft_channel_regs.py" "$O/die_plan.0.json" --report "$O/ft_channel_regs.json" --add-stations --max-add 3 > "$O/die_plan.json"
python3 "$T/gen.py" latency "$O/die_plan.json" --inplace --out "$O/lat"
cp -r "$D/cores" "$D/census" "$D/core_conns.json" "$D/cells_evidence.json" "$D/die_io.json" "$D"/l1_cores_v3*.json "$O/"
# R8: the kv44 bind's bus groups (bound on v3.8x; claude/kv-bind-1024r @1de24d72a bound_kv44) -> fault exempt ->
# invariant split -> rebased onto the v3.9 lane latency -> landing pads (--bus leaf --replica type, as run_v36.sh)
mkdir -p "$O/r8" && cp "$D"/r8/*.py "$O/r8/"
gzip -dc "$D/r8/kv44_bus_groups.json.gz" > "$O/r8/bg_kv44.json"
python3 "$D/r8/r8_fault_exempt.py" "$O/r8/bg_kv44.json" "$O/r8/bg_fx.json"
python3 "$D/r8/r8_invariant_split.py" "$O/die_plan.json" "$O/r8/bg_fx.json" "$O/r8/bg_split.json"
python3 "$D/r8/r8_rebase.py" "$O/die_plan.json" "$O/r8/bg_split.json" "$D/r8/kv44_bind_latency.json.gz" "$O/r8/bus_groups.json"
rm "$O/r8/bg_kv44.json" "$O/r8/bg_fx.json" "$O/r8/bg_split.json"
python3 "$T/gen.py" latency "$O/die_plan.json" --inplace --out "$O/lat" --groups "$O/r8/bus_groups.json" --bus leaf --replica type --fold-r8
cp "$O/lat/qwen_kvsys_r8_landing.json" "$O/r8/"
python3 "$D/lat_delta_v39.py" "$IN" "$O/die_plan.json" "$O/lat_delta_v39.json" "$O/lat/qwen_kvsys_latency.json"
python3 "$T/reset_tree.py" offsets "$O/die_plan.json" --out "$O/reset_offsets.json" > /dev/null
python3 "$T/check.py" "$O/die_plan.json" --landing "$O/r8/qwen_kvsys_r8_landing.json" --out "$O/g0x"
python3 "$T/check.py" "$O/die_plan.json" --completeness --landing "$O/r8/qwen_kvsys_r8_landing.json" --out "$O/g0cx"
