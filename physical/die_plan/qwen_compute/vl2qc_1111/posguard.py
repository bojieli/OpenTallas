"""VISLAYOUT2-QC position guard (COORD 23:26 R1 guard): after kit gen, prove the re-layout positions survived.
Checks: every plan hard core -> macro_place.tcl location within TOL (track snap) and same orient; every plan count-strap
site -> an io.tcl strap_* pin at that xy; K/grt_transition.json mode + image; K/flow_tag.
usage: posguard.py PLAN.json TYPE KITDIR [--mode edge_outline] [--tag TAG]  -> prints one PASS/FAIL line + details, rc 0/1"""
import json, re, sys, argparse
from pathlib import Path
ap = argparse.ArgumentParser(); ap.add_argument("plan"); ap.add_argument("type"); ap.add_argument("kit")
ap.add_argument("--mode", default="edge_outline"); ap.add_argument("--tag", default="flow-20261108-ef-qc"); ap.add_argument("--tol", type=float, default=0.06)
a = ap.parse_args()
t = json.loads(Path(a.plan).read_text())["partition_types"][a.type]
K = Path(a.kit); bad = []; n_ok = 0
mp = {}
for ln in ((K / "macro_place.tcl").read_text() if (K / "macro_place.tcl").exists() else "").splitlines():
    m = re.search(r"-macro_name \{(.+?)\} -location \{([\d.]+) ([\d.]+)\} -orientation (\w+)", ln)
    if m:
        mp[m.group(1).replace("\\[", "[").replace("\\]", "]")] = (float(m.group(2)), float(m.group(3)), m.group(4))
for c in t.get("hard_cores") or []:
    inst = c.get("inst") or c.get("name"); x, y = c["origin_um"]; o = c.get("orient", "R0")
    k = mp.get(inst)
    if not k:
        bad.append(f"core {inst} missing in macro_place.tcl"); continue
    if abs(k[0] - x) > a.tol or abs(k[1] - y) > a.tol or k[2] != o:
        bad.append(f"core {inst} plan ({x},{y},{o}) kit ({k[0]},{k[1]},{k[2]})")
    else:
        n_ok += 1
io = (K / "io.tcl").read_text() if (K / "io.tcl").exists() else ""
pins = [(float(m.group(1)), float(m.group(2))) for m in re.finditer(r"-pin_name \{strap_[^}]*\} -layer \w+ -location \{([\d.]+) ([\d.]+)\}", io)]
ns = 0
for s in t.get("count_straps") or []:
    for xy in s.get("sites_um") or []:
        ns += 1
        if not any(abs(px - xy[0]) <= a.tol and abs(py - xy[1]) <= a.tol for px, py in pins):
            bad.append(f"strap site {xy} not on an io.tcl strap pin")
try:
    g = json.loads((K / "grt_transition.json").read_text())
    if g.get("mode") != a.mode or "grtoff" not in g.get("image", ""):
        bad.append(f"grt_transition {g}")
except Exception as e:
    bad.append(f"grt_transition.json missing ({e.__class__.__name__})")
tag = (K / "flow_tag").read_text().strip() if (K / "flow_tag").exists() else ""
if tag != a.tag:
    bad.append(f"flow_tag {tag!r} != {a.tag!r}")
print(f"POSGUARD {'PASS' if not bad else 'FAIL'} {a.type}: cores {n_ok}/{len(t.get('hard_cores') or [])} at plan xy+orient, "
      f"strap sites {ns - sum(1 for b in bad if b.startswith('strap'))}/{ns}, mode/tag {'ok' if not any(b.startswith(('grt', 'flow')) for b in bad) else 'BAD'}")
for b in bad[:20]:
    print("  ", b)
sys.exit(1 if bad else 0)
