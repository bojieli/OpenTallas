#!/bin/bash
# One case of the quant_wide gate, for the closure loop's composition gates (tools/ref_tile/composition_gates.json:
# quant_wide = WQ 2, quant_wide_ov = WQ 3 OVERLAP 1).  The loop wants one bench per verdict (a positive bench that
# passes, a mutant that fails), and run_qdq_wide.sh builds and judges all cases at once, so this wrapper runs
# run_qdq_wide.sh of the SNAPSHOT IT IS CALLED FROM once per shared directory (flock; the sibling benches reuse the
# result) and then judges the one case asked for from its own log and exit code.
# usage (repo root): [WQ=2|3 OVERLAP=0|1 QDQ_DEFS=...] tools/hgi_unit_tput/run_qdq_wide_gate.sh <shared out dir> <case> [vectors dir]
#   case: m0 | w3 | sk   exact positives (sk: lane-0 acknowledgements delayed 40 cycles; WQ 3 only)
#         m1 | w1 | r2   mutants: header A bit, lane-to-sector map, premature retirement (WQ 3 only)
# exit 0 when the case PASSes in simulation; exit 1 with "QDQ_WIDE_CASE FAIL <case>" when it fails in simulation;
# exit 2 when the case did not build or did not run (never a mutant's expected failure).
set -uo pipefail
out=$(realpath -m "$1"); c=$2; here=$(cd "$(dirname "$0")" && pwd)
vec=$(realpath "${3:-$here/vectors/qdqvec}")
[ -s "$vec/recs.txt" ] || { echo "QDQ_WIDE_CASE ERROR no vectors at $vec"; exit 2; }
mkdir -p "$out"
(
  flock 9
  if [ ! -e "$out/ran" ]; then
    bash "$here/run_qdq_wide.sh" "$vec" "$out" > "$out/runner.log" 2>&1; echo $? > "$out/runner.rc"
    touch "$out/ran"
  fi
) 9> "$out/.lock"
[ -x "$out/$c.obj/sim" ] || { echo "QDQ_WIDE_CASE ERROR $c: no simulator built"; tail -5 "$out/$c.build" 2>/dev/null; exit 2; }
[ -s "$out/$c.log" ] || { echo "QDQ_WIDE_CASE ERROR $c: no simulation log"; exit 2; }
grep -E "PASS HGI_QDQ_WIDE_TPUT|FATAL|MISMATCH" "$out/$c.log" | head -5
if grep -q "PASS HGI_QDQ_WIDE_TPUT" "$out/$c.log" && [ "$(cat "$out/$c.rc" 2>/dev/null || echo 0)" = 0 ]; then
  echo "QDQ_WIDE_CASE PASS $c"; exit 0
fi
grep -qE "FATAL|MISMATCH" "$out/$c.log" || { echo "QDQ_WIDE_CASE ERROR $c: neither PASS nor a checked failure"; exit 2; }
echo "QDQ_WIDE_CASE FAIL $c"; exit 1
