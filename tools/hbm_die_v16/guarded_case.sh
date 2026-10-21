#!/bin/bash
# Run on the fleet. Required source-bound GEN facts are produced by the planner;
# absent/incomplete facts stop before GRT. A successful execution is diagnostic
# evidence only: strict bind, native views and final physical gates still apply.
# guarded_case.sh CASE CONTRACT FACTS [--check-only]
set -uo pipefail
CASE=$(readlink -f "$1"); CONTRACT=$(readlink -f "$2"); FACTS=$(readlink -f "$3")
TOOLS=$(cd "$(dirname "$0")/.." && pwd)
OUT=$CASE/safety_chain
mkdir -p "$OUT"
python3 - "$CASE" "$CONTRACT" "$FACTS" <<'PY' || exit 1
import hashlib,json,sys
from pathlib import Path
case,contract,facts=map(Path,sys.argv[1:])
if not facts.is_file():
    raise SystemExit('GEN_SAFETY FAIL: source-bound channel/crossing facts missing; no GRT')
f=json.loads(facts.read_text())
for key,path in [('contract',contract),('manifest',(case/'manifest.json')),('die_v',(case/'die.v'))]:
    actual=hashlib.sha256(path.read_bytes()).hexdigest()
    if (f.get('input_sha256') or {}).get(key)!=actual:
        raise SystemExit(f'GEN_SAFETY FAIL: facts do not match actual {key}; no GRT')
if not all(f.get(k) for k in ('channels','regions','crossings','wires')):
    raise SystemExit('GEN_SAFETY FAIL: full-die channel/region/crossing/wire census required; no GRT')
tcl=(case/'run.tcl').read_text()
if 'set_routing_layers -signal M4-M8 -clock M7-M9' not in tcl:
    raise SystemExit('GEN_SAFETY FAIL: actual signal routing must be M4-M8; M9 PG/clock only')
if 'set_wire_rc -signal -layer M8' not in tcl or 'define_corners tt ff' not in tcl:
    raise SystemExit('GEN_SAFETY FAIL: M8 RC and TT+FF required in actual case')
PY
python3 "$TOOLS/hbm_die_v16/d4g_reach_check.py" "$CASE" "$CONTRACT" --reset-fails \
  --out "$OUT/reach_check.json" --all "$OUT/reach_failures.json" > "$OUT/reach_check.log" 2>&1 || {
  cat "$OUT/reach_check.log"; exit 1;
}
python3 - "$OUT/reach_check.json" "$FACTS" <<'PY' || exit 1
import json,sys
r,f=(json.load(open(p)) for p in sys.argv[1:])
if len(f['wires']) != r['buses_checked']:
    raise SystemExit('GEN_SAFETY FAIL: facts wire census does not match actual placed-pin bus census')
PY
python3 "$TOOLS/die_safety/gen_check.py" --design hbm --facts "$FACTS" \
  --hbm-reach "$OUT/reach_check.json" --out "$OUT/gen_safety.json" --packet "$OUT/GEN_PACKET.json" \
  > "$OUT/gen_safety.log" 2>&1 || { cat "$OUT/gen_safety.log"; exit 1; }
python3 - "$OUT/gen_safety.json" <<'PY' || exit 1
import json,sys
r=json.load(open(sys.argv[1]))
if not r.get('physical_qualification_eligible') or not r.get('coverage_complete'):
    raise SystemExit('GEN_SAFETY FAIL: complete C1/C2/W1/W2 source-bound coverage required before GRT')
PY
[ "${4:-}" = --check-only ] && exit 0
bash "$CASE/run.sh" > "$OUT/route_driver.log" 2>&1
RC=$?
[ -s "$CASE/out/run.exit" ] && [ "$(cat "$CASE/out/run.exit")" = 0 ] || RC=1
# A missing ODB is an explicit NOT_RUN failure; never substitute analytical IR.
OT_IR_DESIGN=hbm bash "$TOOLS/die_safety/ir_step.sh" "$CASE/out/grt.odb" "$OUT/ir" "$CASE/out/run.log" \
  > "$OUT/ir.log" 2>&1 || RC=1
cat "$OUT/ir.log"
for F in paths_tt_max.txt paths_ff_min.txt; do
  [ -s "$CASE/out/$F" ] || { echo "DIE_STA NOT_RUN: $F missing"; RC=1; }
done
echo "HBM_GUARDED_CHAIN rc=$RC (execution evidence only; not a release verdict)"
exit "$RC"
