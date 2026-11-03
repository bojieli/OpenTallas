#!/bin/bash
# DIE-S81-51/MEM pilot: GEN + GEN_LINT + KIT_PREFLIGHT for one svc type with the class memory-closure bound
# (same recipe as TOK-DS-4 T7 canary3). Usage: pilot.sh <type> <closed bound> [<kit rtl dir>]
set -euo pipefail
T=$1; CB=$2; SRC_RTL=$3
M=/srv/opentallas-scratch2/claude/die-s81-51/mem; K=$M/pilot/$T; W=$M/wt
S=/srv/opentallas-scratch2/claude/wt/kit-wave-15-s81b
rm -rf "$K"; mkdir -p "$K"; cp -a "$SRC_RTL" "$K/rtl"; cp $M/out1/ot_t7_*_capture_candidate.sv "$K/rtl/" 2>/dev/null || true
python3 -I - "$K" "$SRC_RTL" "$T" "$CB" <<'PY'
from pathlib import Path
import sys, json
K = Path(sys.argv[1]); old = sys.argv[2].rstrip('/'); T = sys.argv[3]; cb = Path(sys.argv[4]); root = K / 'rtl'
for f in root.rglob('*'):
    if f.is_file() and f.suffix in ('.f', '.json', '.sv', '.v'):
        f.write_text(f.read_text().replace(old, str(root)))
bound = root / f's81p_{T}_bound.sv'
if cb.name != 'NONE':
    bound.write_text(cb.read_text())
    kids = [str(root / f'ot_t7_{c}_capture_candidate.sv') for c in ('pmem', 'pvq', 'land')]
    for fl in ('kit_rtl.f', 'kit_rtl_sim.f'):
        p = root / fl; L = p.read_text().split('\n'); i = L.index(str(bound)); L[i+1:i+1] = kids; p.write_text('\n'.join(L))
    j = json.loads((root / 'kit_rtl.json').read_text())
    i = j['files'].index(str(bound)); j['files'][i+1:i+1] = kids
    (root / 'kit_rtl.json').write_text(json.dumps(j, indent=1))
PY
cd "$W"
python3 tools/die_plan/gen.py phys physical/die_plan/s81/plan_h2_2249.json --out "$K/gen" --types "$T" --rtl-root "$S" --kit-rtl "$T=$K/rtl/kit_rtl.f" --hold-ff-margin 0 --max-wire-um 100 --clock-landing "$S/physical/die_plan/s81/h2_2249/landed_sidecar_h2.json" > "$K/gen.log" 2>&1
set +e
python3 tools/die_plan/kit_gen_lint.py "$K/gen/$T" --plan-dir "$S/physical/die_plan/s81" --mem 8 > "$K/gen_lint.log" 2>&1
echo "gen_lint rc=$?" > "$K/summary.txt"
python3 tools/die_plan/kit_preflight.py "$K/gen/$T" --plan-dir "$S/physical/die_plan/s81" --out "$K/preflight.json" > "$K/preflight.log" 2>&1
echo "preflight rc=$?" >> "$K/summary.txt"
cat "$K/summary.txt"
