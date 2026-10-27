#!/usr/bin/env bash
# KV-P8-PLAN 10-23: emit KV plan v3.9 from source = the v3.3 -> v3.8h chain on the plan_v39 view:
#   (1) ctlv4: pvw ctl + all 4 vports per side in pv_*_4 (plan_v39.assign_blocks; OT_V39_CTLV4=0 = off)
#   (2) widened lattice (plan_v39 COLW_V39 / ROW_V39; env OT_V39_COLW, OT_V39_ROW)
#   (3) post_v39p.py: hg / hgi / pc / pv hard cores re-placed for the new outlines + N/S face windows spread over the
#       full face (type-frame, per column family) -> core_pins_v37q.py (top-down pins at the new sites) -> post_v37p.py
# Chain order (each step as in run_v34/35/36/37c/38h; the census rows / map are regenerated from the v3.9 stage1):
#   plan_v39 -> emit_v39 -> post_v32 -> census_rows_v32 -> post_v34 -> post_v35 -> post_v36 (+ R8 pads) -> post_v37c
#   -> post_v37k -> post_v37s (via post_v37s_v39) -> post_v37p -> post_v38t -> post_v38h -> post_v39p -> core_pins_v37q -> post_v37p
#   -> gen.py latency -> R8 pads -> G0 / G0C -> g2_channels_v37q (per-gap table) -> lane cycle deltas vs main (lat_delta_v39.py)
# usage: run_v39.sh OUTDIR [BG (BINDER2 bus_groups.json)] [RTL_DIR (bound partition netlists, binder3 kv39 rtl/)]
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd); R=$(cd "$D/../../.." && pwd)
O=${1:?output directory}; mkdir -p "$O"; O=$(cd "$O" && pwd)
BG=${2:-}; RTL=${3:-/home/ubuntu/scratch/binder3-1023/kv39/rtl}
T=${OT_DIE_PLAN_TOOLS:-$R/tools/die_plan}
if [ -z "$BG" ]; then BG=$O/bg2.json; zcat "$D/bind/bus_groups_binder2.json.gz" > "$BG"; fi
A=$D/asbuilt_rtl6_e33504a6f.json.gz
python3 "$D/plan_v39.py" --asbuilt "$A" --out "$O/stage1_v39.json.gz"
python3 "$D/emit_v39.py" --stage1 "$O/stage1_v39.json.gz" --asbuilt "$A" --out "$O/raw.json" --report "$O/plan_report_v39.json"
python3 "$D/post_v32.py" "$O/raw.json" "$O/stage1_v39.json.gz" "$D/bind/v32_inputs.json.gz" > "$O/die_plan.json"
(cd "$O" && python3 "$D/census_rows_v32.py" "$O/stage1_v39.json.gz" "$A")
python3 "$D/post_v34.py" "$O/die_plan.json" "$O/census/census_map_v32.json" "$O/census/census_map_v34.json"
cp "$D/census/bitcon_rtl6.json.gz" "$O/census/"
python3 "$D/post_v35.py" "$O/die_plan.json" > "$O/die_plan_35.json"
python3 "$D/post_v36.py" "$O/die_plan_35.json" > "$O/die_plan.json"; rm "$O/die_plan_35.json"
python3 "$T/gen.py" latency "$O/die_plan.json" --inplace --out "$O/lat36" > /dev/null
python3 "$D/post_v37c.py" "$O/die_plan.json" > "$O/die_plan_c.json"
python3 "$D/post_v37k.py" "$O/die_plan_c.json" > "$O/die_plan_k.json"
python3 "$D/post_v37s_v39.py" "$O/die_plan_k.json" > "$O/die_plan_s.json"
cp -r "$D/cores" "$D/core_conns.json" "$D/cells_evidence.json" "$D"/l1_cores_v3*.json "$O/"
python3 "$D/post_v37p.py" "$O/die_plan_s.json" "$D" > "$O/die_plan_p.json"
python3 "$D/post_v38t.py" "$O/die_plan_p.json" > "$O/die_plan_t.json"
python3 "$D/post_v38h.py" "$O/die_plan_t.json" "$D" > "$O/die_plan_h.json"
rm "$O"/die_plan_c.json "$O"/die_plan_k.json "$O"/die_plan_s.json "$O"/die_plan_p.json "$O"/die_plan_t.json
mv "$O/die_plan_h.json" "$O/die_plan_v38h.json"     # v3.9 lattice + ctlv4 through v3.8h (base of the core re-place)
python3 "$D/post_v39p.py" "$O/die_plan_v38h.json" > "$O/die_plan.json"
python3 "$D/core_pins_v37q.py" "$O/die_plan.json" "$RTL" "$O"
python3 "$D/post_v37p.py" "$O/die_plan.json" "$O" > "$O/die_plan_p.json" && mv "$O/die_plan_p.json" "$O/die_plan.json"
python3 "$T/gen.py" latency "$O/die_plan.json" --inplace --out "$O/lat" > /dev/null
mkdir -p "$O/r8"      # R8 table on the final v3.9 plan (main ran it at v3.6; v3.9 changes lanes, so it is re-derived here)
python3 "$D/r8/r8_fault_exempt.py" "$BG" "$O/r8/bg_fx.json"
python3 "$D/r8/r8_invariant_split.py" "$O/die_plan.json" "$O/r8/bg_fx.json" "$O/r8/bus_groups.json" && rm "$O/r8/bg_fx.json"
python3 "$T/r8.py" pads "$O/die_plan.json" "$O/r8/bus_groups.json" --out "$O/r8" --bus leaf --replica type
python3 "$T/check.py" "$O/die_plan.json" --png --out "$O/g0"
python3 "$T/check.py" "$O/die_plan.json" --completeness --out "$O/g0c" || true   # hub_Wi host children: KV-P8-HUB
python3 "$D/lat_delta_v39.py" "$D/die_plan.json" "$O/die_plan.json" > "$O/lat_delta_v39.json"
[ "${OT_V39_NO_G2:-0}" = 1 ] || python3 "$D/g2_channels_v37q.py" "$O" "$RTL" "$O/g2_channels_v39.json" all
