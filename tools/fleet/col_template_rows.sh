#!/bin/bash
# FABLE-TYPE-REDUCE-S81-COL rows (COORD 11-19): merge the S81 col template groups below 51.
# usage: col_template_rows.sh TREE BASE_PLAN SIDECAR OUT_DIR [--all-members]
#   TREE = a tree holding tools at main (type_template commits).  SIDECAR = the landed sidecar of BASE_PLAN (collector + count_aligned).
#   Writes OUT_DIR/plan_tt.json, sidecar_tt.json and the reports.  Plan level only: CA compose, bind, G0 and LATCHECK are the event's gates.
# Measured on D8e df7446e48ba9 (schema validate 0 errors): 51 kits -> 25 plan layouts, 20 once CA compose has applied the one ring depth;
#   --all-members (plain tiles take the family landing contract with tied children): 20 -> 15.
set -euo pipefail
T=$1; BASE=$2; SIDE=$3; OUT=$4; MODE=${5:-}
mkdir -p "$OUT"
# A: reset keep-outs union per sibling group: every position of a group carries the same reset tree and rst_o pins
python3 -I "$T/tools/fleet/col_typemerge.py" keepouts "$BASE" "$OUT/a_keepouts.json" > "$OUT/a_keepouts.report.json"
# C: one clock landing contract per family, unused children tied (collector-form members only unless --all-members).
#    --keep-taps: the union of added taps breaks the tap spacing rule on col_h9_r2 / col_h9_r0_p2 (10 schema errors), so taps stay per type
python3 -I "$T/tools/die_plan/cland_col_superset.py" "$OUT/a_keepouts.json" "$SIDE" "$OUT/c_superset.json" "$OUT/c_sidecar.json" \
    $([ "$MODE" = "--all-members" ] || echo --collector-only) --keep-taps --report "$OUT/c_superset.report.json" > "$OUT/c_superset.out"
# B: one ring depth per sibling group and bus in the count-aligned table (count_straps width follows the depth at CA compose)
python3 -I "$T/tools/fleet/col_typemerge.py" depth "$OUT/c_superset.json" "$OUT/c_sidecar.json" "$OUT/sidecar_tt.json" > "$OUT/b_depth.report.json"
# flag: every col type is a template candidate; the wave groups them by plan layout key + bound RTL key
python3 -I "$T/tools/fleet/type_template.py" flag "$OUT/c_superset.json" "$OUT/plan_tt.json" "col_h*"
python3 -I "$T/tools/fleet/col_typemerge.py" groups "$OUT/plan_tt.json" | tail -1
echo "ROWS_DONE $OUT/plan_tt.json $(sha256sum "$OUT/plan_tt.json" | cut -c1-12) $OUT/sidecar_tt.json $(sha256sum "$OUT/sidecar_tt.json" | cut -c1-12)"
