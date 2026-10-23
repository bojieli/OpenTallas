#!/usr/bin/env python3
"""A0-REPACK (10-23) first-principles flyline model of an A0 ROM-leaf parent floorplan.

Input: a measured group census (a0_groups.py on a placed ODB dump: std-cell groups, group->group / group->child / port bit
counts) and a floorplan (outline, hard-child origins + orientations, tile pin bus positions).  The std-cell groups are
placed by a quadratic (bit-weighted mean) solve with every hard-child pin bus and tile pin bus fixed -- the same
wirelength objective GPL starts from, without spreading.  Output: bit-weighted Manhattan flyline (bit-mm), the worst
group-to-group distance per edge class, and the per-edge table.  The same model scores the old and the new plan."""
import json, math, re, sys, collections

CHILD = {"ROM": (172.8, 110.16), "LSL": (99.792, 140.4), "NODE": (47.52, 432.0)}
# pin bus anchors in the child's LEF frame: (face, y) -- from the views' LEFs (lefpins census 10-23)
ANCH = {"ROM": {"in": ("W", 21.0), "out": ("W", 27.5)},
        "LSL": {"in": ("E", 50.0), "out": ("E", 120.0)},
        "NODE": {"ab": ("W", 110.8), "y": ("W", 362.2), "tout": ("W", 261.7), "td": ("E", 261.7)}}

def child_kind(g):
    return "ROM" if g.startswith("ROM") else "LSL" if g.startswith("LSL") else "NODE" if g == "NODE" else None

def anchor(ch, g, role):
    k = child_kind(g); w, h = CHILD[k]; x0, y0, o = ch[g]
    face, ly = ANCH[k][role]
    lx = 0.0 if face == "W" else w
    if o in ("MY", "R180"): lx = w - lx
    if o in ("MX", "R180"): ly = h - ly
    return (x0 + lx, y0 + ly)

def role(kind, src_is_child, other):
    if kind == "ROM": return "out" if src_is_child else "in"
    if kind == "LSL": return "out" if src_is_child else "in"
    if kind == "NODE":
        if src_is_child: return "tout" if other == "TOUT" else "y"
        return "td" if other.startswith("TOR") else "ab"

def solve(census, plan, iters=400):
    ch = {g: tuple(v) for g, v in plan["children"].items()}
    ports = {k: tuple(v) for k, v in plan["ports"].items()}
    edges = [(a, b, n) for a, b, n in census["bits"] if n > 0]
    soft = sorted({x for a, b, n in edges for x in (a, b) if not child_kind(x) and not x.startswith("P_")})
    # fixed endpoints per edge
    def fixed(x, other, src):
        k = child_kind(x)
        if k: return anchor(ch, x, role(k, src, other))
        if x.startswith("P_"): return ports.get(x)
        return None
    W, H = plan["outline"]
    pos = {g: [W / 2, H / 2] for g in soft}
    for g in soft:   # seed: plan hint if any
        if g in plan.get("seed", {}): pos[g] = list(plan["seed"][g])
    fixed_soft = plan.get("fixed", {})      # fenced groups: held at their fence centre
    for g, v in fixed_soft.items():
        if g in pos: pos[g] = list(v)
    for _ in range(iters):
        acc = {g: [0.0, 0.0, 0.0] for g in soft}
        for a, b, n in edges:
            if a not in ch and not a.startswith("P_") and a not in soft: continue
            pa = fixed(a, b, True) or (tuple(pos[a]) if a in pos else None)
            pb = fixed(b, a, False) or (tuple(pos[b]) if b in pos else None)
            if pa is None or pb is None: continue
            w = float(n)           # linear: one net per bit, as the placer sees it
            if a in acc: acc[a][0] += w * pb[0]; acc[a][1] += w * pb[1]; acc[a][2] += w
            if b in acc: acc[b][0] += w * pa[0]; acc[b][1] += w * pa[1]; acc[b][2] += w
        for g, (sx, sy, sw) in acc.items():
            if sw and g not in fixed_soft: pos[g] = [0.5 * pos[g][0] + 0.5 * sx / sw, 0.5 * pos[g][1] + 0.5 * sy / sw]
    tot = 0.0; per = []; cls = collections.defaultdict(lambda: [0, 0.0, 0.0])
    for a, b, n in edges:
        pa = fixed(a, b, True) or (tuple(pos[a]) if a in pos else None)
        pb = fixed(b, a, False) or (tuple(pos[b]) if b in pos else None)
        if pa is None or pb is None: continue
        d = abs(pa[0] - pb[0]) + abs(pa[1] - pb[1])
        tot += n * d; per.append((a, b, n, round(d, 1)))
        c = re.sub(r"\d", "", a) + ">" + re.sub(r"\d", "", b)
        cls[c][0] += n; cls[c][1] += n * d; cls[c][2] = max(cls[c][2], d)
    return {"bit_mm": round(tot / 1000, 1), "pos": {g: [round(v, 1) for v in p] for g, p in pos.items()},
            "edges": sorted(per, key=lambda e: -e[2] * e[3]),
            "classes": {c: {"bits": v[0], "bit_mm": round(v[1] / 1000, 1), "max_um": round(v[2], 1)} for c, v in
                        sorted(cls.items(), key=lambda t: -t[1][1])}}

if __name__ == "__main__":
    census = json.load(open(sys.argv[1])); plan = json.load(open(sys.argv[2]))
    r = solve(census, plan)
    print("bit-mm", r["bit_mm"])
    for c, v in list(r["classes"].items())[:20]: print(f"  {c:16s} bits {v['bits']:6d} bit-mm {v['bit_mm']:7.1f} max {v['max_um']:6.1f}")
    if len(sys.argv) > 3: json.dump(r, open(sys.argv[3], "w"), indent=1)

FENCE_MAP = {"rsw": ["RW_sw"], "rnw": ["RW_nw"], "rse": ["RW_se"], "rne": ["RW_ne"], "dw": ["DW"], "de": ["DE"],
             "hub": ["HUB"], "dwr": [f"TWW{g}" for g in range(8)], "der": [f"TWE{g}" for g in range(8)],
             **{f"tx{g}": [f"TX{g}"] for g in range(8)}}

def fences(tcl):
    """fence centres of a qrl_groups regions Tcl -> {census group: [x, y]}"""
    out = {}
    for m in re.finditer(r"name (\w+) type EXCLUSIVE .*? boxes \{\{([\d. ]+)\}\}", open(tcl).read()):
        x0, y0, x1, y1 = map(float, m.group(2).split())
        for g in FENCE_MAP.get(m.group(1), []):
            out[g] = [(x0 + x1) / 2, (y0 + y1) / 2]
    return out
