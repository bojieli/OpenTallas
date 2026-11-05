#!/usr/bin/env python3
"""HBM-REFORM-B5 d44v part 26, after mk_split: station ends on the rel_id tiles.  The tile pin tables are shared across MX/MY instances, so a pin can land far from the old slot pin its station chain ends at.
For each internal station with an end <inst>.<port> on a tile: the end moves to the pin mean of that instance; if the end hop is over 360 um, the nearest regs spread evenly along the HV path.  Register count, bits and order stay, so cycles do not change.
    relax_p26.py PLAN_DIR PREFIX_RE"""
import json, re, sys
pl = sys.argv[1]; PF = re.compile(sys.argv[2]); LIM = 360.0
P = json.load(open(pl + "/die_plan.json")); cache = {}
man = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])
def pin(hc, inst, port):
    h = hc[inst]; f = h["pins_file"]
    if f not in cache: cache[f] = json.load(open(pl + "/" + f))
    pts = [p for p in cache[f] if p["name"] == port or p["name"].startswith(port + "[")]
    if not pts: return None
    W, H = h["outline_um"]; o = h.get("orient", "R0"); ox, oy = h["origin_um"]
    xs = [W - p["x"] if o in ("MY", "R180") else p["x"] for p in pts]; ys = [H - p["y"] if o in ("MX", "R180") else p["y"] for p in pts]
    return [round(ox + sum(xs) / len(xs), 3), round(oy + sum(ys) / len(ys), 3)]
def clear(pt, rects):
    for x0, y0, x1, y1 in rects:
        if x0 < pt[0] < x1 and y0 < pt[1] < y1:
            ds = [(pt[0] - x0, 0, x0 - 4.32), (x1 - pt[0], 0, x1 + 4.32), (pt[1] - y0, 1, y0 - 4.32), (y1 - pt[1], 1, y1 + 4.32)]
            _, a, v = min(ds); pt[a] = round(v, 3)
    return pt
def spread(a, b, n):
    """n points evenly on the HV path a -> b (long leg first)."""
    L = man(a, b); xf = abs(b[0] - a[0]) >= abs(b[1] - a[1]); out = []
    for i in range(1, n + 1):
        s = L * i / (n + 1); dx = abs(b[0] - a[0]); dy = abs(b[1] - a[1]); sx = 1 if b[0] >= a[0] else -1; sy = 1 if b[1] >= a[1] else -1
        if xf: x = a[0] + sx * min(s, dx); y = a[1] + sy * max(0, s - dx)
        else: y = a[1] + sy * min(s, dy); x = a[0] + sx * max(0, s - dy)
        out.append([round(x, 3), round(y, 3)])
    return out
n = moved = 0; worst0 = worst1 = 0.0; left = []
for tn, t in P["partition_types"].items():
    hc = {h["inst"]: h for h in t.get("hard_cores") or []}
    rects = [(h["origin_um"][0], h["origin_um"][1], h["origin_um"][0] + h["outline_um"][0], h["origin_um"][1] + h["outline_um"][1]) for h in hc.values()]
    for st in t.get("internal_stations") or []:
        for end, key, last in (("launch", "from_um", False), ("capture", "to_um", True)):
            e = st.get(end)
            if not isinstance(e, str): continue
            inst, _, port = e.partition(".")
            if not port or not PF.match(inst) or inst not in hc: continue
            q = pin(hc, inst, port)
            if q is None: continue
            n += 1; st[key] = q; r = st.get("regs_um") or []
            if not r: continue
            chain = r[::-1] if last else list(r)                   # chain[0] = reg next to the tile pin
            other = st["from_um" if last else "to_um"]; d0 = man(q, chain[0]); worst0 = max(worst0, d0)
            if d0 > LIM:
                pts = chain + [other]
                for w in range(1, len(chain) + 1):
                    if man(q, pts[w]) / (w + 1) <= LIM or w == len(chain):
                        chain[:w] = [clear(p, rects) for p in spread(q, pts[w], w)]; break
                moved += 1
            st["regs_um"] = chain[::-1] if last else chain
            d1 = man(q, st["regs_um"][-1 if last else 0]); worst1 = max(worst1, d1)
            if d1 > LIM + 60: left.append((tn, e, round(d1)))
json.dump(P, open(pl + "/die_plan.json", "w"), indent=1); open(pl + "/die_plan.json", "a").write("\n")
print("ends", n, "relaxed", moved, "worst end hop", round(worst0), "->", round(worst1), "still long", len(left), left[:6])
