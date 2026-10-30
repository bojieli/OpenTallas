#!/usr/bin/env python3
"""DIE-HBM-32: plan event d32q = BASE (d31t) + idx_query N-face pin spread (HBM-CORES-KITS-26 00:32 ASK, AUTO-GEOM
partial_face FAIL: 593 N-face signal pins packed at 0.096-um pitch on x 51.6-108.8, 10.4/um M5).
Fix-only pin-table change of ot_hbm_idx_query_static (170.64 x 164.16, both hub halves, 4 instances): the 593 N-face
signal pins keep their ORDER, layer (M5), y and size and are re-spaced at 0.240 um pitch from x 10.104 (span 10.104..152.184,
4.2/um <= budgets 6/um); the 4 clk_bank pins at x 0.98 and every S/E/W pin are unchanged.  The N face meets hub soft
logic only (no abutting hard core: nearest sfustore 8.64-um street on the side, keybuf 34.56 um), so no neighbour
face moves.  NEW files only (no write through hardlinks of BASE).  usage: mk_d32q.py BASE OUT"""
import json, subprocess, sys
from pathlib import Path
base, out = Path(sys.argv[1]), Path(sys.argv[2])
OLD = "cores/ot_hbm_idx_query_static__170.64x164.16__canon__d16f__codex_g21__fr28.json"
NEW = "cores/ot_hbm_idx_query_static__170.64x164.16__canon__d16f__codex_g21__fr28__d32q.json"
H, X0, PITCH = 164.16, 10.104, 0.240   # on the M5 plan track grid (offset 0.024, pitch 0.048)
if out.exists():
    sys.exit(f"{out} exists (refuse to overwrite)")
subprocess.check_call(["cp", "-al", str(base), str(out)])
def wnew(rel, txt):
    p = out / rel
    if p.exists() or p.is_symlink():
        p.unlink()
    p.write_text(txt)
pins = json.load(open(base / OLD))
nsig = sorted([q for q in pins if q["y"] > H - 1 and not q["name"].startswith("clk")], key=lambda q: q["x"])
for i, q in enumerate(nsig):
    q["x"] = round(X0 + i * PITCH, 3)
xs = [q["x"] for q in nsig]
assert len(set(xs)) == len(xs) and xs[-1] < 170.64 - 5, xs[-1]
wnew(NEW, json.dumps(pins, indent=1) + "\n")
P = json.load(open(base / "die_plan.json"))
n = 0
for tn, t in P["partition_types"].items():
    for hc in t.get("hard_cores", []):
        if hc.get("pins_file") == OLD:
            hc["pins_file"] = NEW; n += 1
assert n == 4, n
wnew("die_plan.json", json.dumps(P, indent=1) + "\n")
rep = dict(lane="DIE-HBM-32", base=str(base), event="d32q idx_query N-face pin spread", pins_file=NEW,
           n_signal_pins_moved=len(nsig), x_span=[xs[0], xs[-1]], pitch_um=PITCH, density_per_um=round(len(nsig) / (xs[-1] - xs[0]), 2),
           instances=n)
wnew("d32q_event_report.json", json.dumps(rep, indent=1) + "\n")
print(json.dumps(rep))
