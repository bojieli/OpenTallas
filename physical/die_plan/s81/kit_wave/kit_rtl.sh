#!/bin/bash
# Export the exact current bound S81 partition for a kit-wave item.
# env TYPE/OUT/PLAN (kit_wave.py script mode, cwd = wave source checkout) -> $OUT/kit_rtl.f + kit_rtl.json (defines).
# Class types whose instances differ in parameters are kitted only when every differing parameter is an image
# selector of black-box hard cores (image_params.py image proves it; the instance is named, never implicit).
# Never replace an unsigned hard core by a shell.
set -euo pipefail
: "${TYPE:?TYPE must be a plan type}" "${OUT:?OUT must be a fresh kit RTL directory}" "${PLAN:?PLAN must name the plan}"
BIND_OUT=${S81_BIND_OUT:-/srv/opentallas-scratch2/claude/die-s81-34/rebind/out}
ASBUILT=${S81_ASBUILT:-physical/die_plan/s81/bind/asbuilt_b178_coll_s13pfunc.json}
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
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
# bind.f of the strict bind may name a removed worktree: read it through a private overlay (kit-rtl bind.f preference)
OV="${OUT%/}_bindov"
python3 -I "$HERE/image_params.py" overlay "$BIND_OUT" "$PWD" "$OV" > "$OUT/bind_overlay.json"
python3 -I "$HERE/image_params.py" image "$OV" "$PLAN" "$TYPE" > "$OUT/image_params.json"
INST=$(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1]))["instance"] or "")' "$OUT/image_params.json")
python3 -I tools/die_plan/bind.py kit-rtl "$PLAN" --out "$OV" --asbuilt "$ASBUILT" --type "$TYPE" --kit "$OUT" \
    ${INST:+--instance "$INST"}
python3 -I - "$OUT" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
f = [Path(x) for x in (p / "kit_rtl.f").read_text().splitlines() if x.strip()]
assert f and all(x.is_file() for x in f), "S81_KIT_RTL: missing source closure"
r = json.loads((p / "kit_rtl.json").read_text())
# DIE-S81-36 / COORD ruling 10-30 (seqhost ASK option b): declared constant spare outputs, exact match only.  seqhost__t1
# unit_o4: lane unit__seqhost__gunit is 267 on all 14 plan records; the as-built seqhost drives 265 bits and gunit reads
# 265, so the 2 top bits stay registered constants (pins unchanged).  Any other / different spare set still fails.
DECLARED_SPARE_OUT = {"seqhost__t1": [{"port": "unit_o4", "bits": 2}]}
spare = sorted((x["port"], x["bits"]) for x in r.get("spare_out_bits") or [])
assert spare == sorted((x["port"], x["bits"]) for x in DECLARED_SPARE_OUT.get(r["plan_type"], [])), \
    "S81_KIT_RTL: constant spare outputs require a plan fix (or a COORD-declared exception)"
im = json.loads((p / "image_params.json").read_text())
r["s81_image_params"] = im
(p / "kit_rtl.json").write_text(json.dumps(r, indent=1))
print("S81_KIT_RTL PASS", r["plan_type"], len(f), "sources", "instance", im["instance"] or "-",
      "image_params", len(im["image_params"]), "of", im["instances"], "instances")
PY
