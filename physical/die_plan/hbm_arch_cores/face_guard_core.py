"""ELEM-HBM: tools/die_plan/face_guard.py on a hard-core netlist (CP1-R10 gate, unchanged checker).
Differences from the partition call only in the inputs: the skip regex = the core's clock AND reset pins (freeze.json:
reset pins are async reset taps, not face registers), and scalar plan pins are matched by name (face_guard's planned-bit
list formats every row as bus[bit]).
    python3 face_guard_core.py NETLIST.v KITDIR      -> KITDIR/face_guard.json, exit 1 = FAIL
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import face_guard as FG  # noqa: E402
import straps as STR

net, kd = sys.argv[1], Path(sys.argv[2])
fz = json.loads((kd / "freeze.json").read_text())
skip = "^(" + "|".join(re.escape(re.sub(r"\[\d+\]$", "", n)) for n in fz["clocks"] + fz["resets"]) + ")$"
pins = [p for p in json.loads((kd / "pins.json").read_text()) if p["bit"] is not None and not re.match(skip, p["bus"])]
r = FG.guard(Path(net).read_text(), fz["design"], skip_re=skip, pins=pins, straps=STR.kit_straps(kd))
r["skip_re"] = skip
(kd / "face_guard.json").write_text(json.dumps(r, indent=1) + "\n")
print(f"FACE_GUARD {r['verdict']} top {fz['design']} checked {r.get('checked')} ok {r.get('ok')} fails "
      f"{ {k: len(v) for k, v in r['fails'].items()} }")
sys.exit(0 if r["verdict"] == "PASS" else 1)
