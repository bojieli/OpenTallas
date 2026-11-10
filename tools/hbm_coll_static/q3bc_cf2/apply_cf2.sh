#!/bin/bash
# HBM-CORES-B q3bc CF2 (11-10): build the CF2 programme-check form of a flat q3 body netlist from its source at HEAD.
#   SF1 TBF (patch_sf.py, cycle-exact) + CF2 (patch_cf2.py: u_flow read + check_row registered, scan end +1 edge,
#   parent timing hard_v5_q3cf2 in tools/hbm_coll_static/parent_timing.py).  Works on body_ctl and on the v8x body_core
#   (same u_program net names; every edit asserts its exact anchor).
# usage: apply_cf2.sh IN OUT [mutant]
set -euo pipefail
H=$(cd "$(dirname "$0")" && pwd)
IN=$1; OUT=$2; MUT=${3:-}; T=$(mktemp -d "${OUT}.tmp.XXXX")
M=$(grep -m1 -oE '^module [A-Za-z0-9_]+' "$IN" | cut -d' ' -f2)
sed -E "s/^module $M\b/module ot_hfd_coll_q3_body_ctl_x/" "$IN" > "$T/x.sv"
python3 -I "$H/patch_sf.py" "$T/x.sv" "$T/sf.sv" TBF
python3 -I "$H/patch_cf2.py" "$T/sf.sv" "$T/cf2.sv" $MUT
sed -E "s/^module ot_hfd_coll_q3_body_ctl_x\b/module $M/" "$T/cf2.sv" > "$OUT"
rm -rf "$T"
