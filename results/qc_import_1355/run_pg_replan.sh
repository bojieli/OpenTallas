#!/bin/bash
# Correct the inherited quoting bug; partial upstream geometry is diagnostic only.
set -euo pipefail
V=$1
Q=/srv/opentallas-scratch2/claude
R=$Q/codex-qc-import-1355
B=$Q/die-qc36
I=$Q/codex-qc-import-0824
O=$R/pa_$V
mkdir -p "$O"
python3 - "$I/clock_landing_reserved.json" "$B/backbone_bb1/joint_clock_reserved.json" "$B/backbone_bb1/backbone_plan.json" "$O" <<'PY'
import json,sys
from pathlib import Path
a,b,plan,out=sys.argv[1:];p=json.load(open(plan));o=Path(out)
json.dump(json.load(open(a))+json.load(open(b)),open(o/"joint_reserved.json","w"),separators=(",",":"))
json.dump(dict(source_status=p["status"],source_failures=len(p["failures"]),diagnostic_partial=bool(p["failures"]),scope="PG construction only; never die GRT/freeze evidence"),open(o/"upstream_status.json","w"),indent=2)
PY
docker run --rm --name codex-qci1355-pa$V-$$ --memory=96g --memory-swap=96g --cpus=4 -v "$Q:$Q" -w "$R" -e PYTHONPATH="$I/pydeps" python:3.12 bash -c "set -e; trap 'chown -R 1000:1000 $O' EXIT; if [ $V = A ]; then python $I/src/plan_access.py --input $B/readback_resite --clock-seed $B/backbone_bb1/clock_base_resite.json --joint-clock-reserved $O/joint_reserved.json --reserved-power $I/nativepg/bridges/reserved_bridges.json --out $O; else python $B/pg_access_plan_b7a872287.py --input $B/readback_resite --clock-seed $B/backbone_bb1/clock_base_resite.json --joint-clock-reserved $O/joint_reserved.json --m9-select cover --m8-landing fallback --out $O; fi > $O/run.log 2>&1"
