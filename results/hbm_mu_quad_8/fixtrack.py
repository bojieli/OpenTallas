#!/usr/bin/env python3
"""HBM-MU-QUAD-8: put hard-core pins back on the plan tracks after the QUAD-7 8.64-lattice origin snap (shifts like +1.080 /
-3.240 are not multiples of the 0.048 / 0.036 pitches).  Per hard core with off-track pins (type frame, check.py on_track
semantics): choose the smallest sub-lattice track_offset_um (|d| < 2.16) that puts the most pins on track (x for V layers, y for
H layers), origin stays on the 8.64 lattice; station endpoints of that core move with the offset change.
Then any single pin still off track whose layer direction does not match its face (e.g. an M5 pin on an E face) is listed;
--snap-pins moves those pins (core frame, all instances of the pins file) to the nearest on-track point on the face edge
inside the outline.  usage: fixtrack.py PLANDIR [--snap-pins]"""
import json, sys, re, collections
from pathlib import Path
import numpy as np
d = Path(sys.argv[1]); SNAP = "--snap-pins" in sys.argv
p = json.loads((d / "die_plan.json").read_text())
LY = dict(M2=("H", .036, .045), M3=("V", .036, .009), M4=("H", .048, .024), M5=("V", .048, .024), M6=("H", .064, .032), M7=("V", .064, .032))
def tr(o, W, H, x, y): return {"R0": (x, y), "MY": (W-x, y), "MX": (x, H-y), "R180": (W-x, H-y)}[o or "R0"]
def offk(c, ln): _, pt, of = LY[ln]; k = (c-of)/pt; return abs(k-round(k)) >= 1e-4
cache = {}; rep = dict(cores_offset=[], pins_snapped=[], residual=[])
def pins_of(pf):
    if pf not in cache:
        js = json.loads((d / pf).read_text()); cache[pf] = js.get("pins", js) if isinstance(js, dict) else js
    return cache[pf]
def tf(c):  # type-frame pin coords without track offset
    W, H = c["outline_um"]; ox, oy = c["origin_um"]; out = []
    for q in pins_of(c["pins_file"]):
        if q.get("layer") not in LY: continue
        x, y = tr(c.get("orient"), W, H, q["x"], q["y"]); out.append((q, q["layer"], ox+x, oy+y))
    return out
cand = np.round(np.arange(-2.15, 2.15, 0.001), 3); cand = cand[np.argsort(np.abs(cand), kind="stable")]
def best(vals):  # vals: [(coord, layer)] -> offset putting most on track (smallest |d| among ties)
    if not vals: return 0.0, 0
    best_d, best_bad = 0.0, None
    for dd in cand:
        bad = sum(offk(v+dd, ln) for v, ln in vals)
        if best_bad is None or bad < best_bad: best_d, best_bad = float(dd), bad
        if bad == 0: break
    return best_d, best_bad
moved = collections.defaultdict(dict)
for tn, t in p["partition_types"].items():
    for c in t.get("hard_cores", []) or []:
        if not c.get("pins_file"): continue
        P = tf(c); dx0, dy0 = c.get("track_offset_um", [0.0, 0.0])
        nbad = sum(offk((x+dx0) if LY[ln][0] == "V" else (y+dy0), ln) for q, ln, x, y in P)
        if nbad == 0: continue
        V = [(x, ln) for q, ln, x, y in P if LY[ln][0] == "V"]; Hh = [(y, ln) for q, ln, x, y in P if LY[ln][0] == "H"]
        # most pins dominate: offsets chosen on the subset of pins whose face matches the layer direction
        W, Hc = c["outline_um"]
        def edge_ok(q):
            fx = min(q["x"], W-q["x"]); fy = min(q["y"], Hc-q["y"])
            return (LY[q["layer"]][0] == "H") == (fx <= fy)        # H-layer pins on E/W faces, V-layer pins on N/S faces
        Vg = [(x, ln) for q, ln, x, y in P if LY[ln][0] == "V" and edge_ok(q)] or V
        Hg = [(y, ln) for q, ln, x, y in P if LY[ln][0] == "H" and edge_ok(q)] or Hh
        dx, bx = best(Vg); dy, by = best(Hg)
        if (dx, dy) != (dx0, dy0):
            c["track_offset_um"] = [dx, dy]; c["note"] = c.get("note", "") + f"; QUAD-8 track_offset {dx0},{dy0} -> {dx},{dy} (pins back on plan tracks after 8.64 snap)"
            moved[tn][c["inst"]] = (dx-dx0, dy-dy0)
            rep["cores_offset"].append((tn, c["inst"], nbad, [dx, dy], bx, by))
        if SNAP:
            for q, ln, x, y in P:
                _, pt, of = LY[ln]; o = c.get("orient")
                if LY[ln][0] == "V" and offk(x+dx, ln):
                    k = round((x+dx-of)/pt); nx_ = of + k*pt - dx - c["origin_um"][0]   # type-frame target -> core frame
                    cx = nx_ if o in (None, "R0", "MX") else W - nx_
                    cx = min(max(cx, 0.0), W)
                    if abs(cx-q["x"]) < pt: rep["pins_snapped"].append((c["pins_file"], q["name"], q["x"], round(cx, 4))); q["x"] = round(cx, 4)
                if LY[ln][0] == "H" and offk(y+dy, ln):
                    k = round((y+dy-of)/pt); ny_ = of + k*pt - dy - c["origin_um"][1]
                    cy = ny_ if o in (None, "R0", "MY") else Hc - ny_
                    cy = min(max(cy, 0.0), Hc)
                    if abs(cy-q["y"]) < pt: rep["pins_snapped"].append((c["pins_file"], q["name"], q["y"], round(cy, 4))); q["y"] = round(cy, 4)
for tn, mv in moved.items():  # endpoints of moved cores follow the offset change
    t = p["partition_types"][tn]
    for e in t.get("internal_stations", []) or []:
        for side, key in (("launch", "from_um"), ("capture", "to_um")):
            s = str(e.get(side, "")).split(".")[0]
            for inst, (ddx, ddy) in mv.items():
                if s in (inst, re.sub(r"__q\d+$", "", inst)):
                    e[key] = [round(e[key][0]+ddx, 3), round(e[key][1]+ddy, 3)]; break
(d / "die_plan.json").write_text(json.dumps(p, indent=1) + "\n")
if SNAP:
    for pf in {x[0] for x in rep["pins_snapped"]}: (d / pf).write_text(json.dumps(cache[pf], indent=1) + "\n")
(d / "fixtrack_report.json").write_text(json.dumps(rep, indent=1, default=int) + "\n")
print("cores re-offset", len(rep["cores_offset"])); [print(" ", r) for r in rep["cores_offset"][:30]]
print("pins snapped", len(rep["pins_snapped"]), rep["pins_snapped"][:12])
