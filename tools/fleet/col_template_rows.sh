#!/bin/bash
# FABLE-TYPE-REDUCE-S81-COL rows for D8h: col template groups 51 -> 19 (collector-only) or 14 (--all-members).
# usage: mk_rows_d8h_template.sh TREE BASE_PLAN SIDECAR OUT_DIR [CA_TABLE] [--all-members]
#   TREE = S81 src tree holding tools at main >= the type_template commits.  Writes OUT_DIR/plan_tt.json, sidecar_tt.json,
#   (ca_tt.json when CA_TABLE is given) and reports.  Plan-level only: compose, bind, G0 and LATCHECK are the event's own gates.
set -euo pipefail
T=$1; BASE=$2; SIDE=$3; OUT=$4; CA=${5:-}; MODE=${6:-}
[ "$CA" = "--all-members" ] && { MODE=$CA; CA=; }
mkdir -p "$OUT"
# A: reset keep-outs union per sibling group (every position of a group carries the same reset tree and rst_o pins)
python3 -I "$T/tools/fleet/col_typemerge.py" keepouts "$BASE" "$OUT/a_keepouts.json" > "$OUT/a_keepouts.report.json"
# C: one clock landing contract per family (collector-form members only unless --all-members)
python3 -I "$T/tools/die_plan/cland_col_superset.py" "$OUT/a_keepouts.json" "$SIDE" "$OUT/c_superset.json" "$OUT/sidecar_tt.json" \
    $([ "$MODE" = "--all-members" ] || echo --collector-only) --report "$OUT/c_superset.report.json" > "$OUT/c_superset.out"
# B: one ring depth per sibling group and bus (count_straps width follows the depth at CA compose)
if [ -n "$CA" ]; then
  python3 -I "$T/tools/fleet/col_typemerge.py" depth "$OUT/c_superset.json" "$CA" "$OUT/ca_tt.json" > "$OUT/b_depth.report.json"
fi
# flag: every col type is a template candidate; the wave groups them by plan layout key + bound RTL key
python3 -I "$T/tools/fleet/type_template.py" flag "$OUT/c_superset.json" "$OUT/plan_tt.json" "col_h*"
python3 -I "$T/tools/fleet/col_typemerge.py" groups "$OUT/plan_tt.json" | tail -1
echo "ROWS_DONE $OUT/plan_tt.json $(sha256sum "$OUT/plan_tt.json" | cut -c1-12)"
