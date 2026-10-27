#!/usr/bin/env python3
"""KV-PLAN-EVAL: hub_Ei FT vertical-leg column demand in a plan (per-bit sites)."""
import json, sys, collections
P = json.load(open(sys.argv[1])); tn = sys.argv[2] if len(sys.argv) > 2 else "kv3_hub_Ei"
t = P["partition_types"][tn]; W, H = t["outline_um"]
BIN = 15.0
vert = collections.defaultdict(list)   # bin -> list of (y0,y1,bits,slot)
diag = 0; hops = 0; over405 = []; legs = []
for s in t["ft_slots"]:
    regs = s.get("regs_um")
    if not regs: continue
    w = int(s["width"])
    bs = s.get("bit_sites_um")
    # per-bit path: regs[0] (in pin) -> bit sites (per station) -> out face
    paths = []
    if bs and len(bs) == len(regs) - 1:
        for b in range(w):
            pts = [regs[0]] + [st[b % len(st)] for st in bs]
            paths.append(pts)
        mult = 1
    else:
        paths = [regs]; mult = w
    for pts in paths:
        for a, c in zip(pts, pts[1:]):
            hops += 1
            dx, dy = abs(a[0]-c[0]), abs(a[1]-c[1])
            if dx > 1 and dy > 1: diag += 1
            if dx + dy > 405: over405.append((s["name"], round(dx+dy, 1)))
            if dy > 1:
                x = c[0] if dx > 1 else a[0]   # assume horizontal then vertical (vertical leg at the later x)
                vert[int(x // BIN)].append((min(a[1], c[1]), max(a[1], c[1]), mult, s["name"]))
                legs.append((x, a[1], c[1], mult, s["name"]))
# max over y of crossing bits per bin
res = []
for b, L in vert.items():
    ys = sorted({y for l in L for y in l[:2]})
    best = (0, None)
    for y in ys:
        yy = y + 0.01
        n = sum(m for y0, y1, m, _ in L if y0 < yy < y1)
        if n > best[0]: best = (n, yy)
    slots = len({l[3] for l in L})
    res.append(dict(x0=b*BIN, x1=(b+1)*BIN, max_bits=best[0], at_y=best[1], slots=slots))
res.sort(key=lambda r: -r["max_bits"])
# capacity: vertical M5+M7 (and M3) tracks per 15 um at 0.6 cut_avail; M5 pitch 0.144? use plan budget if present
out = dict(type=tn, outline=[W, H], bin_um=BIN, slots_sited=sum(1 for s in t["ft_slots"] if s.get("regs_um")),
           slots=len(t["ft_slots"]), bits=sum(int(s["width"]) for s in t["ft_slots"]), hops=hops, diagonal_hops=diag,
           hops_over_405=len(over405), worst_hop=max([h for _, h in over405], default=None), top_columns=res[:8])
json.dump(dict(summary=out, legs=legs), open(sys.argv[3], "w"))
print(json.dumps(out, indent=1))
