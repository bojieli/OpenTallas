#!/usr/bin/env python3
"""C17: fast core_faces-only run (same function check.py G0C uses) + per-port away list with core metadata."""
import sys, json, re, math
from pathlib import Path
sys.path.insert(0, "/srv/opentallas-scratch2/claude/wt/codex-hbm-plan-1351/tools/die_plan")
import check as CK
import schema as S
plan = Path(sys.argv[1]).resolve()
raw = S.load(str(plan))
P = S.Plan(raw, plan)
R = CK.Report(True)
pc = {}
CK.FACE_AWAY_COS_SAVE = CK.FACE_AWAY_COS
out = CK.check_core_faces(P, R, plan.parent, None, max_msgs=10**6, per_core=pc)
errs = [i for i in R.items if i["level"] == "ERROR"]
print(json.dumps(out))
for e in errs:
    print("ERR", e["msg"][:400])
if len(sys.argv) > 2:
    Path(sys.argv[2]).write_text(json.dumps(dict(summary=out, errors=[e["msg"] for e in errs]), indent=1))
# detail: parse away msgs, attach hc metadata
rx = re.compile(r"type (\S+) core (\S+) port (\S+): (\d+) pins on face (\S+) face away .*mean cos ([-+.\d]+), (\d+) pins on the far side \(re-pin to face (\w)\)")
hcm = {}
users = {}
for tn, t in P.types.items():
    for hc in t.get("hard_cores", []):
        hcm[(tn, hc["inst"])] = hc
        users.setdefault(hc.get("pins_file"), []).append((tn, hc["inst"], hc.get("orient", "R0")))
rows = []
for e in errs:
    m = rx.search(e["msg"])
    if not m: continue
    tn, ci, lp, n, fc, mc, aw, bf = m.groups()
    hc = hcm[(tn, ci)]
    rows.append(dict(type=tn, core=ci, port=lp, pins=int(n), faces=fc, cos=float(mc), best=bf, orient=hc.get("orient", "R0"),
                     pins_file=hc.get("pins_file"), outline=hc["outline_um"], sel=hc.get("pin_select", {}).get(lp),
                     shared=users.get(hc.get("pins_file"))))
if len(sys.argv) > 3:
    Path(sys.argv[3]).write_text(json.dumps(rows, indent=1))
import collections
c = collections.Counter((r["type"], r["core"], r["orient"], r["pins_file"], len(r["shared"] or [])) for r in rows)
for k, v in sorted(c.items()): print(v, k)
