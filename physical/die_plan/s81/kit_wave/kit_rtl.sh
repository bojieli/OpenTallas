#!/bin/bash
# Export the exact current bound S81 partition for a kit-wave item.
# Class types requiring different parameter value sets remain blocked; never
# select an instance implicitly or replace an unsigned hard core by a shell.
set -euo pipefail
: "${TYPE:?TYPE must be a plan type}" "${OUT:?OUT must be a fresh kit RTL directory}" "${PLAN:?PLAN must name the plan}"
BIND_OUT=${S81_BIND_OUT:-/srv/opentallas-scratch2/claude/die-s81-34/rebind/out}
ASBUILT=${S81_ASBUILT:-physical/die_plan/s81/bind/asbuilt_b178_coll_s13pfunc.json}
python3 -I - "$BIND_OUT" "$PLAN" "$TYPE" <<'PY'
import json, sys
from pathlib import Path
b, plan, typ = sys.argv[1:]
r = json.loads((Path(b) / "bind_report.json").read_text())
e = r["errors"]
assert (len(e) if isinstance(e, list) else e) == 0, "S81_KIT_RTL: strict bind errors"
p = json.loads(Path(plan).read_text())
assert typ in p["partition_types"], "S81_KIT_RTL: unknown plan type"
assert typ in r["types"], "S81_KIT_RTL: type absent from strict bind"
PY
mkdir -p "$OUT"
python3 -I tools/die_plan/bind.py kit-rtl "$PLAN" --out "$BIND_OUT" --asbuilt "$ASBUILT" --type "$TYPE" --kit "$OUT"
python3 -I - "$OUT" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
f = [Path(x) for x in (p / "kit_rtl.f").read_text().splitlines() if x.strip()]
assert f and all(x.is_file() for x in f), "S81_KIT_RTL: missing source closure"
r = json.loads((p / "kit_rtl.json").read_text())
assert not r.get("spare_out_bits"), "S81_KIT_RTL: constant spare outputs require a plan fix"
print("S81_KIT_RTL PASS", r["plan_type"], len(f), "sources")
PY
