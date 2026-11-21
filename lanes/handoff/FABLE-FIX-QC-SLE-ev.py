#!/usr/bin/env python3
"""FABLE-FIX-QC-SLE: per-bit station sites of every per_bit bus chain of one type vs hard-core boxes.
ev.py PLAN TYPE [OVERRIDES.json] [--dump-pins FILE]"""
import json, sys, os, pickle
from pathlib import Path
HERE = Path(os.environ.get("OT_TOOLS", "/srv/opentallas-scratch2/claude/fable-fix-qc-sle/clone/tools/die_plan"))
sys.path[:0] = [str(HERE), str(HERE.parents[1])]
import istation_channel as IC
plan, tn = sys.argv[1], sys.argv[2]
ovr = json.load(open(sys.argv[3])) if len(sys.argv) > 3 and not sys.argv[3].startswith("--") else {}
cache = Path(os.environ.get("EV_CACHE", "/srv/opentallas-scratch2/claude/fable-fix-qc-sle/ev_cache.pkl"))
if cache.exists():
    t, pins = pickle.load(open(cache, "rb"))
else:
    import schema as S, gen_phys
    raw = json.load(open(plan)); P = S.Plan(raw, path=plan); t = P.types[tn]
    pins = {}
    for name, bit, _ln, x, y, f in gen_phys.type_pins(P, tn):
        pins.setdefault(name, {})[int(bit)] = (float(x), float(y), f)
    t = {k: v for k, v in t.items() if k not in ("relay_sites",)}
    pickle.dump((t, pins), open(cache, "wb"))
HALO = float(ovr.get("halo", 0.0))
cores = {}
for c in t.get("hard_cores", []):
    ox, oy = ovr.get("core_origin", {}).get(c["inst"], c["origin_um"]); w, h = c["outline_um"]
    cores[c["inst"]] = (ox, oy, ox + w, oy + h)
def knee(px, py, lx, ly, face, edge, edges, d, geo, order):
    xmin, ymin, xmax, ymax = geo
    if face in "EW":
        normal = max(abs(xmin - lx), abs(xmax - lx)); along = max(abs(ymin - ly), abs(ymax - ly)); cx, cy = lx, py
    else:
        normal = max(abs(ymin - ly), abs(ymax - ly)); along = max(abs(xmin - lx), abs(xmax - lx)); cx, cy = px, ly
    n1, a1 = normal, along
    if order == "along":
        cx, cy = (px, ly) if face in "EW" else (lx, py); n1, a1 = along, normal
    if d == "in": first, second, ax, ay, bx, by = n1, a1, px, py, lx, ly
    else: first, second, ax, ay, bx, by = a1, n1, lx, ly, px, py
    if first < 1e-8: split, worst = 0, second / edges
    elif second < 1e-8: split, worst = edges, first / edges
    else:
        split, worst = -1, 1e99
        for j in range(1, edges):
            w = max(first / j, second / (edges - j))
            if w < worst: worst, split = w, j
    if edge <= split and split:
        f = edge / split; return (ax + f * (cx - ax), ay + f * (cy - ay)), worst, [(ax, ay), (cx, cy), (bx, by)]
    f = (edge - split) / (edges - split); return (cx + f * (bx - cx), cy + f * (by - cy)), worst, [(ax, ay), (cx, cy), (bx, by)]
def inbox(p, halo=0.0):
    for nm, (x0, y0, x1, y1) in cores.items():
        if x0 - halo < p[0] < x1 + halo and y0 - halo < p[1] < y1 + halo: return nm
    return None
def segbox(a, c, tol=0.5):
    out = []
    for nm, (bx0, by0, bx1, by1) in cores.items():
        x0, x1, y0, y1 = min(a[0], c[0]), max(a[0], c[0]), min(a[1], c[1]), max(a[1], c[1])
        if x0 < bx1 - tol and x1 > bx0 + tol and y0 < by1 - tol and y1 > by0 + tol: out.append(nm)
    return out
buses = {b["name"]: b for b in t["buses"]}
tot_in = tot_cross = 0
print("cores", {k: tuple(round(v, 1) for v in bx) for k, bx in cores.items() if k in ("u_ctl", "u_tap")})
for e in t["internal_stations"]:
    if e.get("bit_route") != "per_bit" or not e["conn"].startswith("bus:"): continue
    bus = e["conn"][4:]; b = buses[bus]; o = ovr.get("chains", {}).get(bus, {})
    if b["dir"] != "out" and not o.get("force"):   # in chains with lane pads are packed rows (regs_um), listed below
        regs = o.get("regs_um", e["regs_um"])
        hit = [(i, inbox(r, 30.0)) for i, r in enumerate(regs) if inbox(r, 30.0)]
        print(f"IN   {bus:20s} n={len(regs)} bits={e['bits']:5d} regs={[(round(r[0]),round(r[1])) for r in regs]} near_core(30um)={hit}")
        continue
    n = int(o.get("n", len(e["regs_um"]))); lx, ly = o.get("leaf_um", e["leaf_um"]); face = b["face"]
    order = o.get("leg_order", e.get("leg_order", "normal_first")); chan = o.get("channel_um")
    pp = pins[bus]; W = max(pp)
    xs = [p[0] for p in pp.values()]; ys = [p[1] for p in pp.values()]; geo = (min(xs), min(ys), max(xs), max(ys))
    off = float(o.get("offset", 0.0))
    if face == "W": lx2, ly2 = lx - off, ly
    elif face == "E": lx2, ly2 = lx + off, ly
    elif face == "S": lx2, ly2 = lx, ly - off
    else: lx2, ly2 = lx, ly + off
    nin = [0] * n; ncross = 0; worst = 0; ex = []; cross_c = {}
    for bit, (px, py, _f) in pp.items():
        if order == "channel":
            lo, hi = chan
            pts = IC.path(px, py, lx2, ly2, face, "out", IC.column(lo, hi, bit, W + 1)); L = IC.length(pts)
            st = [IC.point_at(pts, L * (k + 1) / (n + 1)) for k in range(n)]; worst = max(worst, L / (n + 1))
        else:
            st = []
            for k in range(n):
                s, w, pts = knee(px, py, lx2, ly2, face, k + 1, n + 1, "out", geo, "along" if order == "along_first" else "normal")
                st.append(s); worst = max(worst, w)
        for k, s in enumerate(st):
            if inbox(s, HALO): nin[k] += 1
        cc = set()
        for a, c in zip(pts, pts[1:]): cc |= set(segbox(a, c))
        for c in cc: cross_c[c] = cross_c.get(c, 0) + 1
        if cc: ncross += 1
        if bit in (0, W // 2, W): ex.append([(round(s[0]), round(s[1])) for s in st])
    tot_in += sum(nin); tot_cross += ncross
    print(f"OUT  {bus:20s} {face} n={n} bits={W+1:5d} leaf=({lx:.0f},{ly:.0f}) {order:12s} worst_hop={worst:6.1f} sites_in_core/stage={nin} routes_crossing={ncross} {cross_c}\n       ex bit0/mid/last {ex}")
print("TOTAL sites in core", tot_in, "routes crossing", tot_cross)
for s in t.get("ft_slots", []):
    regs = s.get("regs_um") or []
    print("FT  ", s["name"], s["in_face"], s["out_face"], s["width"], [(round(r[0]), round(r[1])) for r in regs], [inbox(r, 30.0) for r in regs])
