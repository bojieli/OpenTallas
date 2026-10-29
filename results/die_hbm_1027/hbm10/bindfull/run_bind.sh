#!/bin/sh
# DIE-HBM-10 10-28: HBM strict bind with the EXISTING alignment checks, logs kept for the bind READY.
#   elab   (bind_elab: sources + release_full no-stub check, manifest key release_full)
#   bind --strict   (bind.py: connectivity / UNMAPPED / TIED / UNPLANNED / TYPE_SPLIT ... fail closed)
#   verify (bind_verify: re-elaborate the generated RTL, prove connectivity) -- only when the strict bind passes
# usage: run_bind.sh PLAN.json ASBUILT.json OUT_DIR [MEM_GB]   (run from the repo root, on a fleet host)
set -u
PLAN=$1; AB=$2; OUT=$3; MEM=${4:-48}
mkdir -p "$OUT/logs"
python3 tools/die_plan/bind.py elab "$PLAN" --out "$OUT" --asbuilt "$AB" --mem "$MEM" --allow-external-paths \
    > "$OUT/logs/elab.log" 2>&1; E=$?
echo "elab rc=$E" | tee "$OUT/logs/summary.txt"
[ $E -eq 0 ] || exit $E
python3 tools/die_plan/bind.py bind "$PLAN" --out "$OUT" --asbuilt "$AB" --strict --allow-external-paths \
    > "$OUT/logs/bind_strict.log" 2>&1; B=$?
echo "bind --strict rc=$B" | tee -a "$OUT/logs/summary.txt"
if [ $B -eq 0 ]; then
    python3 tools/die_plan/bind.py verify "$PLAN" --out "$OUT" --asbuilt "$AB" --mem "$MEM" --allow-external-paths \
        > "$OUT/logs/verify.log" 2>&1; V=$?
    echo "verify rc=$V" | tee -a "$OUT/logs/summary.txt"
else
    echo "verify SKIPPED (strict bind failed closed)" | tee -a "$OUT/logs/summary.txt"
fi
python3 - "$OUT" <<'EOF' | tee -a "$OUT/logs/summary.txt"
import json, sys, collections
from pathlib import Path
r = Path(sys.argv[1]) / "bind_report.json"
if r.exists():
    d = json.loads(r.read_text())
    errs = d.get("errors") or d.get("strict_errors") or []
    k = collections.Counter(str(e).split()[0] for e in errs)
    print("strict errors", len(errs), dict(k.most_common()))
EOF
