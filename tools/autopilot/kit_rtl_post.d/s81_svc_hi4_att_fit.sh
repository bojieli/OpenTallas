#!/bin/bash
# S81 svc hi4 att kit-RTL post step (OPUS-FIX-S81-SVC-R9 2026-11-22, COORD-approved).
# Runs after `bind.py kit-rtl` (kit_wave.py kit_rtl_post_cmd inlines every tools/autopilot/kit_rtl_post.d/*.sh),
# cwd = wave source checkout; env TYPE, OUT (kit RTL dir with kit_rtl.json), PLAN (the kit plan).
# Class: the J8 hi4 split piece svc_hi_dsdv_svc_rs__t4_att binds as svc_hi_dsdv_svc_rs__t4_att_part_bound, which the
# svc memory closure (s81_svc_memory.sh, s81p_svc_* only) skips, so its staging/PMEM memories stayed soft (~601k
# cells, over the 400k cap).  This step applies the proved hi4 att memory fit (tools/die_plan/s81_svc_hi4_att_fit.py):
# exact netlist witnesses, fail-closed on any difference.  Every other kit is left byte-identical (exit 0).
set -euo pipefail
: "${TYPE:?TYPE must be a plan type}" "${OUT:?OUT must be the kit RTL directory}" "${PLAN:?PLAN must be the kit plan}"
[ -f "$OUT/kit_rtl.json" ] || { echo "S81_HI4_ATT_FIT: no $OUT/kit_rtl.json" >&2; exit 1; }
BM=$(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1])).get("bound_module") or "")' "$OUT/kit_rtl.json")
[ "$BM" = svc_hi_dsdv_svc_rs__t4_att_part_bound ] || exit 0
T=tools/die_plan/s81_svc_hi4_att_fit.py
[ -f "$T" ] || { echo "S81_HI4_ATT_FIT: $BM needs $T in the wave source ($(pwd))" >&2; exit 1; }
python3 -I "$T" --kit-rtl "$OUT" --plan "$PLAN" --type "$TYPE" --src-tree .
