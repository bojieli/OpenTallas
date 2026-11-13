#!/bin/bash
# S81 kit-RTL post step (HARD-S81-SVC-1, 2026-11-13). Runs after `bind.py kit-rtl` in BOTH kit-wave kit_rtl modes:
#   script mode: kit_rtl.sh calls it;
#   bind mode:   kit_wave.py kit_rtl_post_cmd runs every physical/die_plan/*/kit_wave/kit_rtl_post.sh of the wave
#                source (cwd = wave source checkout).
# env TYPE (plan type), OUT (kit RTL dir holding kit_rtl.json / kit_rtl.f), PLAN (not used here).
# Why one shared step: the svc memory closure was a line of kit_rtl.sh only. When the S81 wave moved to kit_rtl mode
# "bind" (ready12b-A, 11-12 21:46) the step was lost: every svc bound kept its native memories (attn_staging 4 x
# 160x265 per instance, pmem 512x512, land 640x256, pvq 8x2120) and all 16 svc items stopped at GEN_LINT memory_bits.
# The step selects itself from the kit content (bound module s81p_svc_*), never from the wave configuration.
set -euo pipefail
: "${TYPE:?TYPE must be a plan type}" "${OUT:?OUT must be the kit RTL directory}"
[ -f "$OUT/kit_rtl.json" ] || { echo "S81_KIT_RTL_POST: no $OUT/kit_rtl.json" >&2; exit 1; }
BM=$(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1])).get("bound_module") or "")' "$OUT/kit_rtl.json")
case "$BM" in
    s81p_svc_*) ;;
    *) exit 0 ;;                                   # not an S81 svc kit: nothing to do, the kit stays byte-identical
esac
# COORD 11-04 07:34 (5), S81 svc plan event (delta_svc_band_1104): every svc type closes its native memories to the
# MEM v2 generated macros the plan places (T7 class port + idx fit, tools/die_plan/s81_svc_memory_closure.py).
python3 -I tools/die_plan/s81_svc_memory_closure.py --form v2 --kit-rtl "$OUT"
# The receipt must say APPLIED, or NOT_APPLICABLE (a bound without the native helper set, e.g. a later source-level
# macro form). A closure that left a behavioural staging memory behind must not reach GEN.
python3 -I - "$OUT" "$BM" <<'PY'
import json, re, sys
from pathlib import Path
out, bm = Path(sys.argv[1]), sys.argv[2]
rc = out / "memory_closure.json"
st = json.loads(rc.read_text()).get("status") if rc.is_file() else "NOT_APPLICABLE"
assert st in ("APPLIED", "NOT_APPLICABLE"), "S81_KIT_RTL_POST: svc memory closure status %r" % st
b = (out / (bm + ".sv")).read_text()
left = re.findall(r"^\s*ot_hdc_v41x_attn_staging\s+#\([^;]*?SRAM_MACRO\(1'b0\)", b, re.M)
assert not (st == "APPLIED" and left), "S81_KIT_RTL_POST: %d behavioural staging instance(s) left" % len(left)
print("S81_KIT_RTL_POST PASS", bm, "memory_closure", st)
PY
