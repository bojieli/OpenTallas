#!/usr/bin/env bash
# Emit plan v3.7s (KV-P7-V38 10-23) = v3.7r + post_v37s.py (hg|hgi window move + hgi rows on the hg grid)
# for the new sites, G0, G0C and the per-gap channel-demand table.  Lanes / ports unchanged -> the v3.6 latency + R8 tables
# stand.  usage: run_v37q.sh V37P_DIE_PLAN.json OUTDIR [RTL_DIR (binder3 kv39 rtl/)]
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd); R=$(cd "$D/../../.." && pwd)
IN=${1:?v3.7p die_plan.json}; O=${2:?output directory}; RTL=${3:-/home/ubuntu/scratch/binder3-1023/kv39/rtl}; mkdir -p "$O"
T=${OT_DIE_PLAN_TOOLS:-$R/tools/die_plan}
python3 "$D/post_v37r.py" "$IN" > "$O/die_plan_r.json"; python3 "$D/post_v37s.py" "$O/die_plan_r.json" > "$O/die_plan.json"; rm "$O/die_plan_r.json"
cp -r "$D/cores" "$D/census" "$D/cells_evidence.json" "$D"/l1_cores_v3*.json "$D/r8" "$O/"
python3 "$D/core_pins_v37q.py" "$O/die_plan.json" "$RTL" "$O"          # writes $O/cores/*_pins.json, core_conns.json, patch
python3 "$D/post_v37p.py" "$O/die_plan.json" "$O" > "$O/die_plan_p.json" && mv "$O/die_plan_p.json" "$O/die_plan.json"
python3 "$T/check.py" "$O/die_plan.json" --png --out "$O/g0"
python3 "$T/check.py" "$O/die_plan.json" --completeness --out "$O/g0c" || true   # G0C per type (hub_Wi children: KV-P7-HUB)
python3 "$D/g2_channels_v37q.py" "$O" "$RTL" "$O/g2_channels_v37q.json" all
