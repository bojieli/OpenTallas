#!/usr/bin/env bash
# KV-PLAN3 10-25: plan v3.9 -> v3.9e = v3.9d (geom_v39d.py pv column +259.2 / hub_Wi E-W channel / ectlk quarters,
# chan_windows.py channel-mouth pins, core_reface.py) + g3/post_v39e.py (ECTLK quarter real pins with the approved pin
# drop, am g drop, pv_join die-track snap, kvs_ctl re-outline, reset.start broadcast).
#   phase gen:      ... -> G0/G0C (face findings above 6/um expected until the per-type G2 budgets are applied)
#   phase budget:   g3/face_budget.py with the per-type G2 table (hard cores obstructing) -> G0/G0C again
#   usage: run_v39e.sh gen V39_DIE_PLAN.json OUTDIR ECTLK_SV [ECTLK_LIVE.json]
#          run_v39e.sh budget OUTDIR G2_TABLE.json G2_REF
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd); R=$(cd "$D/../../.." && pwd); T="$R/tools/die_plan"
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
IN=${2:?v3.9 die_plan.json}; O=${3:?output directory}; SV=${4:?ectlk columns sv}; LIVE=${5:-}
mkdir -p "$O/cores"; cp -r "$D/cores/." "$O/cores/"
python3 "$D/g3/geom_v39d.py" "$IN" "$O/die_plan_geom.json" --cores-out "$O/cores"
python3 "$D/g3/post_v39e.py" "$O/die_plan_geom.json" --cores "$O/cores" --ectlk-sv "$SV" ${LIVE:+--ectlk-live "$LIVE"} --report "$O/post_v39e.json"
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
python3 "$D/lat_delta_v39.py" "$IN" "$O/die_plan.json" "$O/lat_delta_v39e.json" "$O/lat/qwen_kvsys_latency.json"
python3 "$T/reset_tree.py" offsets "$O/die_plan.json" --out "$O/reset_offsets.json" > /dev/null
gates "$O"
