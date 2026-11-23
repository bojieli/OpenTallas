#!/bin/bash
# S81 svc monolithic attention memory fit kit-RTL post step (FAM-S81-SVC-OWN 2026-11-22).
# Runs after `bind.py kit-rtl` (kit_wave.py kit_rtl_post_cmd inlines every tools/autopilot/kit_rtl_post.d/*.sh; sorts after
# s81_svc_memory.sh), cwd = wave source checkout; env TYPE, OUT (kit RTL dir with kit_rtl.json), PLAN (the kit plan).
# Class: svc_hi rs t4/t5, svc_lo rs t3/t6, svc_hi pvso_entry t1 bind with the native PMEM + attn_staging cones but WITHOUT
# the native pvq memory, so the stock svc memory closure (s81_svc_memory.sh, needs all 4 helpers) is NOT_APPLICABLE and the
# plan's pmem/stage2/tr macro placements had no bound instance (PLAN-SRC-MACRO at place).  tools/die_plan/s81_svc_att_fit_all.py
# applies the proved hi4 att memory fit with witnesses derived per type, fail-closed.  Other kits stay byte-identical (exit 0).
set -euo pipefail
: "${TYPE:?TYPE must be a plan type}" "${OUT:?OUT must be the kit RTL directory}" "${PLAN:?PLAN must be the kit plan}"
[ -f "$OUT/kit_rtl.json" ] || { echo "S81_SVC_ATT_FIT_ALL: no $OUT/kit_rtl.json" >&2; exit 1; }
case "$TYPE" in
    svc_hi_dsdv_svc_rs__t4|svc_hi_dsdv_svc_rs__t5|svc_lo_dsdv_svc_rs__t3|svc_lo_dsdv_svc_rs__t6|svc_hi_dsdv_svc_pvso_entry__t1) ;;
    *) exit 0 ;;
esac
T=tools/die_plan/s81_svc_att_fit_all.py
[ -f "$T" ] || { echo "S81_SVC_ATT_FIT_ALL: $TYPE needs $T in the wave source ($(pwd))" >&2; exit 1; }
python3 -I "$T" --kit-rtl "$OUT" --plan "$PLAN" --type "$TYPE" --src-tree .
