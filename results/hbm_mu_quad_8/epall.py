#!/usr/bin/env python3
"""QUAD-8: distance of every internal_stations launch/capture endpoint that names a hard-core port (inst.port) to the nearest
actual pin of that port (pins_file, orient applied).  --fix moves the endpoint onto the nearest pin of the port on the face
facing the chain's first/last register (ties: nearest) and shifts the adjacent landing register by the same vector if it
was within 60 um of the old endpoint.  usage: epall.py PLANDIR [--fix] [--tol 20]"""
import json, sys, math, re, collections
from pathlib import Path
d = Path(sys.argv[1]); FIX = "--fix" in sys.argv
ONLY = sys.argv[sys.argv.index("--only")+1] if "--only" in sys.argv else None
CONNS = sys.argv[sys.argv.index("--conns")+1] if "--conns" in sys.argv else None
TOL = float(sys.argv[sys.argv.index("--tol")+1]) if "--tol" in sys.argv else 20.0
p = json.loads((d / "die_plan.json").read_text())
def tr(o, W, H, x, y): return {"R0": (x, y), "MY": (W-x, y), "MX": (x, H-y), "R180": (W-x, H-y)}[o or "R0"]
cache = {}
rep = collections.Counter(); worst = []; per_core = collections.Counter()
for tn, t in p["partition_types"].items():
    cores = {}
    for c in t.get("hard_cores", []) or []:
        pf = c.get("pins_file")
        if not pf: continue
        if pf not in cache: cache[pf] = json.loads((d / pf).read_text())
        W, H = c["outline_um"]; ox, oy = c["origin_um"]; dx, dy = c.get("track_offset_um", [0, 0])
        g = collections.defaultdict(list)
        for q in cache[pf]:
            if not isinstance(q, dict) or "name" not in q or "x" not in q: continue
            x, y = tr(c.get("orient"), W, H, q["x"], q["y"]); g[q["name"].split("[")[0]].append((ox+dx+x, oy+dy+y))
        cores[c["inst"]] = g
    for e in t.get("internal_stations", []) or []:
        for side, key, ri in (("launch", "from_um", 0), ("capture", "to_um", -1)):
            s = str(e.get(side, ""))
            if "." not in s: continue
            inst, port = s.split(".", 1)
            cands = [k for k in cores if k == inst or re.sub(r"__q\d+$", "", k) == inst]
            cands = [k for k in cands if port in cores[k]]
            if not cands: rep["port_not_found"] += 1; continue
            old = e[key]
            k = min(cands, key=lambda k: min(math.dist(q, old) for q in cores[k][port]))
            pins = cores[k][port]; dist = min(math.dist(q, old) for q in pins)
            rep["endpoints"] += 1
            if dist <= TOL: rep["on_pin"] += 1; continue
            if (ONLY and not re.search(ONLY, k)) or (CONNS and not re.search(CONNS, e["conn"])):
                rep["off_pin_not_selected"] += 1; per_core[(tn, k)] += 1; worst.append((round(dist, 1), tn, k, port)); continue
            rep["off_pin"] += 1; per_core[(tn, k)] += 1; worst.append((round(dist, 1), tn, k, port))
            if FIX:
                ref = e["regs_um"][ri] if e["regs_um"] else (e["to_um"] if side == "launch" else e["from_um"])
                new = min(pins, key=lambda q: abs(q[0]-ref[0]) + abs(q[1]-ref[1]))
                new = [round(new[0], 3), round(new[1], 3)]
                if e["regs_um"] and math.dist(e["regs_um"][ri], old) < 60:
                    r = e["regs_um"][ri]; e["regs_um"][ri] = [round(r[0]-old[0]+new[0], 3), round(r[1]-old[1]+new[1], 3)]
                e[key] = new; rep["fixed"] += 1
                e["note"] += "; QUAD-8 endpoint onto actual pin"
worst.sort(reverse=True)
print(dict(rep)); print("worst", worst[:12]); print("per core", per_core.most_common(25))
if FIX: (d / "die_plan.json").write_text(json.dumps(p, indent=1) + "\n")
