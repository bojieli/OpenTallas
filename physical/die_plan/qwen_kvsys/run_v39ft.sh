#!/usr/bin/env bash
# KV-FT 10-24: plan v3.8x -> v3.9ft CANDIDATE (NOT main) = post_v39_ft.py MA,MD,MB (+ post_v39_mb.py) + gen.py latency
# + r8.py pads (as main: --bus leaf --replica type) + G0 / G0C + ft audit / before-after report.
#   usage: run_v39ft.sh OUTDIR [MOVES=MA,MD,MB]      (light python, ~2 min)
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd); R=$(cd "$D/../../.." && pwd); T=$R/tools/die_plan
O=${1:?output directory}; M=${2:-MA,MD,MB}; mkdir -p "$O"; O=$(cd "$O" && pwd)
python3 "$D/post_v39_ft.py" "$D/die_plan.json" "$D" "$O" "$M"
cp "$D/census/bitcon_rtl6.json.gz" "$O/census/"
cp -r "$D/cores" "$D/core_conns.json" "$D/cells_evidence.json" "$D/die_io.json" "$D"/l1_cores_v3*.json "$O/"
python3 "$T/gen.py" latency "$O/die_plan.json" --inplace --out "$O/lat" --groups "$O/r8/bus_groups.json"
python3 "$T/r8.py" pads "$O/die_plan.json" "$O/r8/bus_groups.json" --out "$O/r8" --bus leaf --replica type
python3 "$T/check.py" "$O/die_plan.json" --landing "$O/r8/qwen_kvsys_r8_landing.json" --out "$O/g0"
python3 "$T/check.py" "$O/die_plan.json" --completeness --landing "$O/r8/qwen_kvsys_r8_landing.json" --out "$O/g0c" || true
python3 "$D/ft_audit_v39.py" "$D/die_plan.json" --out "$O/audit_v38x" --png "$O/ft_v38x.png" --title "KV v3.8x (main) feedthrough crossings"
python3 "$D/ft_audit_v39.py" "$O/die_plan.json" --out "$O/audit_v39ft" --png "$O/ft_v39ft.png" --title "KV v3.9ft candidate ($M)"
python3 "$D/ft_compare_v39.py" "$D/die_plan.json" "$O/die_plan.json" "$O/audit_v38x" "$O/audit_v39ft" > "$O/ft_v39ft_report.json"
