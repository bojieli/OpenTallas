#!/usr/bin/env python3
"""DIE-HBM-86 d44v part 59 replay on the part 61 stack: DIE-HBM-82-RF mk_p59.py transformation (ot_svgr_top obs_max M5 -> M6 on 8 sites),
packed like every plan event.  mk_p59b.py PLAN_DIR MK_P59 OUT_DIR"""
import gzip, hashlib, json, subprocess, sys, os
d, mk, out = sys.argv[1:4]
tmp_por = f"{out}/por.json"; tmp_new = f"{out}/new.json"; led = f"{out}/ledger.json"
raw = gzip.open(f"{d}/die_plan.json.gz").read(); open(tmp_por, "wb").write(raw)
print(subprocess.run([sys.executable, "-I", mk, tmp_por, tmp_new, led], capture_output=True, text=True).stdout)
new = open(tmp_new, "rb").read()
with open(f"{d}/die_plan.json.gz", "wb") as f:
    with gzip.GzipFile(fileobj=f, mode="wb", mtime=0, filename="") as g: g.write(new)
ev = {"schema": "opentallas.hbm_plan_event.v1", "part": 59, "plan": "d44v", "lane": "DIE-HBM-86, from DIE-HBM-82-RF", "date": "2026-11-07",
      "approved": "COORD: READY only on G0C NEW 0, once vL6 reaches route, with die GRT estimate",
      "what": ["ot_svgr_top obs_max M5 -> M6 on its 8 sites: q_hub_nw and q_hub_ne, u_svg_Q0..3__t"],
      "why": "vL6 is built with M6 open inside the core (GRT M6 use 9.94%, overflow 0)",
      "ledger": "results/die_hbm_1106/rf86_p59/ledger.json"}
p = f"{d}/part59_event.json"
json.dump(ev, open(p, "w"), indent=1); open(p, "a").write("\n")
h = lambda b: hashlib.sha256(b).hexdigest()
s = []
for l in open(f"{d}/SHA256SUMS").read().splitlines():
    a, n = l.split(None, 1)
    if n.strip() in ("die_plan.json.gz", "die_plan.json"):
        s.append(f"{h(new)}  {n.strip()}")
    elif n.strip() != "part59_event.json":
        s.append(l)
s.append(f"{h(open(p, 'rb').read())}  part59_event.json")
open(f"{d}/SHA256SUMS", "w").write("\n".join(s) + "\n")
open(f"{d}/README.md" if os.path.exists(f"{d}/README.md") else f"{d}/README", "a").write(
    "\nEvent part 59 (DIE-HBM-86 11-07, replay of DIE-HBM-82-RF mk_p59.py on the part 61 stack): ot_svgr_top obs_max M5 -> M6 on its 8 sites (q_hub_nw, q_hub_ne, u_svg_Q0..3__t); form vL6 is built with M6 open. No pin, outline or origin change.\n")
os.remove(tmp_por); os.remove(tmp_new)
