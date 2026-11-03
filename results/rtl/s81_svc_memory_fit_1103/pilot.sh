#!/bin/bash
# DIE-S81-51/MEM v2 pilot: kit-RTL apply (tool --form v2 --closed-dir this packet) + GEN + GEN_LINT + KIT_PREFLIGHT.
# Macro views + reset/landing RTL come from this worktree (--rtl-root $W); plan dir from the kit-wave tree.
# Usage: pilot.sh <type> <pristine kit rtl dir>
set -euo pipefail
T=$1; SRC_RTL=${2%/}
M=/srv/opentallas-scratch2/claude/die-s81-51/mem; K=$M/${PILOT_DIR:-pilot_v2}/$T; W=$M/wt
S=/srv/opentallas-scratch2/claude/wt/kit-wave-15-s81b
rm -rf "$K"; mkdir -p "$K"; cp -a "$SRC_RTL" "$K/rtl"
python3 -I - "$K/rtl" "$SRC_RTL" <<"PY"
from pathlib import Path
import os, sys
root = Path(sys.argv[1]); old = sys.argv[2]
for f in root.rglob("*"):
    if f.is_file() and f.suffix in (".f", ".json"):
        t = f.read_text().replace(old, str(root))
        for kv in filter(None, os.environ.get("PILOT_SUBST", "").split(",")):   # pilot-only source swap (stale kit tree)
            t = t.replace(*kv.split("="))
        f.write_text(t)
PY
cd "$W"
python3 tools/die_plan/s81_svc_memory_closure.py --form v2 --kit-rtl "$K/rtl" --closed-dir "$W/results/rtl/s81_svc_memory_fit_1103" > "$K/apply.log" 2>&1
python3 tools/die_plan/gen.py phys physical/die_plan/s81/plan_h2_2249.json --out "$K/gen" --types "$T" --rtl-root "$W" --kit-rtl "$T=$K/rtl/kit_rtl.f" --hold-ff-margin 0 --max-wire-um 100 --clock-landing "$S/physical/die_plan/s81/h2_2249/landed_sidecar_h2.json" > "$K/gen.log" 2>&1
set +e
python3 tools/die_plan/kit_gen_lint.py "$K/gen/$T" --plan-dir "$S/physical/die_plan/s81" --mem 8 > "$K/gen_lint.log" 2>&1
echo "gen_lint rc=$?" > "$K/summary.txt"
python3 tools/die_plan/kit_preflight.py "$K/gen/$T" --plan-dir "$S/physical/die_plan/s81" --out "$K/preflight.json" > "$K/preflight.log" 2>&1
echo "preflight rc=$?" >> "$K/summary.txt"
cat "$K/summary.txt"
