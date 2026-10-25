#!/usr/bin/env bash
# Reproduce the Qwen compute die plan (variant B, COORD 10-23 06:41) from the committed inputs:
#   inputs/qc_census.json.gz  FT-TOOL census of the as-built r50 die (69 blocks, 2518 lane groups)
#   inputs/fp_w.json fp_e.json slice kit floorplans (qfd_dv_slice2_w16real / e16real leaf inventory + face pins)
#   inputs/s8_lp_record.json  slice landed-parent record (tools/landed_parent/lp.py, 210 region crossings)
#   inputs/slice_grid.json    slice region grid from slice_layout_search.py (+ su core <-> lane-group split bits)
# Then: latency table (inplace + SV pkg + compiler JSON), G0 check + G1 render.
#   bash physical/die_plan/qwen_compute/run.sh [VARIANT]      (variant A = archived per-A0 CB plan, written to /tmp)
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd); R=$(cd "$D/../../.." && pwd); T=$R/tools/die_plan; I=$D/inputs
V=${1:-B}; O=$D; [ "$V" = B ] || O=$(mktemp -d /tmp/qc_plan_$V.XXXX)
python3 "$D/gen_plan.py" --variant "$V" --census "$I/qc_census.json.gz" --slice-fp-w "$I/fp_w.json" \
  --slice-fp-e "$I/fp_e.json" --slice-record "$I/s8_lp_record.json" --su-split "$I/slice_grid.json" \
  --slice-face-map "$I/slice2_face_map.json" --out "$O/die_plan.json"
python3 "$D/apply_start_broadcast.py" "$O/die_plan.json"
# PLAN-DELTA/QC 10-25: approved TYPE-REDUCE items on non-PATH types (sle_hc3 -> slw_hc3, E su_lane -> W tables, frozen
# wavefront reset.in_sites); see results/plan_delta_1025/qc/README.md
[ "$V" = B ] && python3 "$R/results/plan_delta_1025/qc/delta_qc.py" "$O/die_plan.json"
python3 "$T/gen.py" latency "$O/die_plan.json" --inplace --out "$O"
# PLAN-TOOL5 die IO windows (die_io.json sidecar, read by check.py): host link = ucie_kv (d2d_rom <-> KV/system die,
# which carries the host SerDes); S0-S2 SerDes = collective links; coll UCIe on the W edge in coll_ucie
python3 "$T/die_io.py" plan "$O/die_plan.json" --out "$O/die_io.json"
python3 "$T/check.py" "$O/die_plan.json" --png --out "$O"
echo "plan -> $O"
