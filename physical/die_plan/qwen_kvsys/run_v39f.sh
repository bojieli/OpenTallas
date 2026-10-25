#!/usr/bin/env bash
# KV-PLAN3F 10-25: plan v3.9e -> v3.9f = TYPE-REDUCE KV (COORD-approved): g3/post_v39f.py (neutral chain-bus names,
# hg_v1_r1..r5 + hg_v2 -> kv3_hg_v1, pc_v2 -> pc_v1, pv N/S pairs that are identical -> one type) + r8/r8_row_publish.py
# (hg row R8 alignment pads -> per-row latency published in lat_v39f/row_latency.json for KV-TOK).
#   phase gen:      V39E_DIR (run_v39e.sh gen output) -> OUTDIR: post_v39f -> fwd_stations -> latency -> R8 (+ row publish) -> folded
#                   latency -> lat delta vs v3.9e -> row latency table -> reset offsets -> G0/G0C
#   phase budget:   as run_v39e.sh budget (g3/face_budget.py with the per-type G2 table) -> G0/G0C again
#   usage: run_v39f.sh gen V39E_DIR OUTDIR
#          run_v39f.sh budget OUTDIR G2_TABLE.json G2_REF
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd); R=$(cd "$D/../../.." && pwd); T="$R/tools/die_plan"
FAMILY=kv3_hg,kv3_hg_v1,kv3_hg_v3
gates() {
  O=$1
  python3 "$T/check.py" "$O/die_plan.json" --landing "$O/r8/qwen_kvsys_r8_landing.json" --out "$O/g0x" || true
  python3 "$T/check.py" "$O/die_plan.json" --completeness --landing "$O/r8/qwen_kvsys_r8_landing.json" --out "$O/g0cx" || true
}
if [ "$1" = budget ]; then
  O=$2
  python3 "$D/g3/face_budget.py" "$O/die_plan.json" --g0 "$O/g0x/g0_report.json" --g2 "$3" --g2-ref "$4" > "$O/face_budget.json"
  cat "$O/face_budget.json"
  gates "$O"
  exit 0
fi
IN=${2:?v3.9e output dir}; O=${3:?output directory}
mkdir -p "$O/cores"; cp -r "$IN/cores/." "$O/cores/"
cp -r "$IN/census" "$IN/cells_evidence.json" "$IN/core_conns.json" "$IN"/l1_cores_v3*.json "$O/"
[ -f "$IN/die_io.json" ] && cp "$IN/die_io.json" "$O/"
python3 "$D/g3/post_v39f.py" "$IN/die_plan.json" "$O/die_plan.json" --side "$O" --report "$O/post_v39f.json"
# KV-KITS fwd_reach (scope add 10-25): FIRM internal stations (in channels) on tap-tree forward legs > 405 um
python3 "$D/g3/fwd_stations_v39f.py" "$O/die_plan.json" "$O/die_plan.json" --report "$O/fwd_stations_v39f.json"
python3 "$T/gen.py" latency "$O/die_plan.json" --inplace --out "$O/lat"
mkdir -p "$O/r8" && cp "$D"/r8/*.py "$O/r8/"
gzip -dc "$D/r8/kv44_bus_groups.json.gz" > "$O/r8/bg_kv44.json"
python3 "$D/r8/r8_fault_exempt.py" "$O/r8/bg_kv44.json" "$O/r8/bg_fx.json"
python3 "$D/r8/r8_invariant_split.py" "$O/die_plan.json" "$O/r8/bg_fx.json" "$O/r8/bg_split.json"
python3 "$D/r8/r8_row_publish.py" "$O/die_plan.json" "$O/r8/bg_split.json" "$O/r8/bg_pub.json" --family "$FAMILY"
python3 "$D/r8/r8_rebase.py" "$O/die_plan.json" "$O/r8/bg_pub.json" "$D/r8/kv44_bind_latency.json.gz" "$O/r8/bus_groups.json"
rm "$O/r8/bg_kv44.json" "$O/r8/bg_fx.json" "$O/r8/bg_split.json" "$O/r8/bg_pub.json"
python3 "$T/gen.py" latency "$O/die_plan.json" --inplace --out "$O/lat" --groups "$O/r8/bus_groups.json" --bus leaf --replica type --fold-r8
cp "$O/lat/qwen_kvsys_r8_landing.json" "$O/r8/"
python3 "$D/lat_delta_v39.py" "$IN/die_plan.json" "$O/die_plan.json" "$O/lat_delta_v39f.json" "$O/lat/qwen_kvsys_latency.json"
python3 "$D/g3/row_latency_v39f.py" "$IN/r8/qwen_kvsys_r8_landing.json" "$O/r8/qwen_kvsys_r8_landing.json" "$O/die_plan.json" \
  --out "$O/lat_v39f/row_latency.json"
python3 "$T/reset_tree.py" offsets "$O/die_plan.json" --out "$O/reset_offsets.json" > /dev/null
gates "$O"
