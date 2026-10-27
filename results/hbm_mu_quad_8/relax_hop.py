#!/usr/bin/env python3
"""HBM-MU-QUAD-8 step 2 for the chains relax_route.py left > GATE: the signal wire may cross a hard core on M6/M7 (cores are OBS <= M5,
12.1a), only the REGISTER sites must sit in a street.  Minimum-hop register placement: layered L1 dilation (radius R) over the free
4.32-um lattice of the type, from the launch pin to the capture pin; backtrack picks one free site per layer.  Count rule as COORD
quad-7: keep the count if feasible, else at most ONE added register; anything else is reported, not forced.
usage: relax_hop.py PLANDIR [R=400] [GATE=405]  (appends to PLANDIR/relax_route_report.json)"""
import json, sys
from pathlib import Path
import numpy as np
d = Path(sys.argv[1]); R = float(sys.argv[2]) if len(sys.argv) > 2 else 400.0; GATE = float(sys.argv[3]) if len(sys.argv) > 3 else 405.0
G, CLEAR = 4.32, 2.16
p = json.loads((d / "die_plan.json").read_text())
rp = json.loads((d / "relax_route_report.json").read_text())
md = lambda a, b: abs(a[0]-b[0]) + abs(a[1]-b[1])
def worst(pts): return max(md(a, b) for a, b in zip(pts, pts[1:]))
out = dict(kept=0, added=[], failing=[])
for tn, t in p["partition_types"].items():
    bad = [e for e in t.get("internal_stations") or [] if worst([e["from_um"]] + e["regs_um"] + [e["to_um"]]) > GATE + 1e-6]
    if not bad: continue
    W, H = t["outline_um"]
    xs = np.arange(G, W - G/2, G); ys = np.arange(G, H - G/2, G)
    ok = np.ones((len(ys), len(xs)), bool)
    for h in t.get("hard_cores", []) or []:
        x, y = h["origin_um"]; w, hh = h["outline_um"]; dx, dy = h.get("track_offset_um", [0, 0])
        ok[np.ix_((ys > y+dy-CLEAR) & (ys < y+dy+hh+CLEAR), (xs > x+dx-CLEAR) & (xs < x+dx+w+CLEAR))] = False
    X, Y = np.meshgrid(xs, ys)
    for e in bad:
        a, b, n = e["from_um"], e["to_um"], len(e["regs_um"]); before = worst([a] + e["regs_um"] + [b])
        layers = [ok & (np.abs(X-a[0]) + np.abs(Y-a[1]) <= R)]
        rr = int(R // G)
        while not (layers[-1] & (np.abs(X-b[0]) + np.abs(Y-b[1]) <= R)).any() and len(layers) < n + 3:
            cur = layers[-1].copy(); acc = cur.copy()
            for _ in range(rr):                      # L1 dilation by rr lattice steps
                s = acc.copy()
                s[1:, :] |= acc[:-1, :]; s[:-1, :] |= acc[1:, :]; s[:, 1:] |= acc[:, :-1]; s[:, :-1] |= acc[:, 1:]
                acc = s
            layers.append(acc & ok)
        k = len(layers)                              # registers needed
        if not (layers[-1] & (np.abs(X-b[0]) + np.abs(Y-b[1]) <= R)).any() or k > n + 1:
            out["failing"].append((tn, e["conn"], n, k, round(before, 1))); continue
        regs = []; cur = b
        for L in reversed(layers):
            m = L & (np.abs(X-cur[0]) + np.abs(Y-cur[1]) <= R)
            iy, ix = np.nonzero(m)
            j = int(np.argmin(np.abs(X[iy, ix]-a[0]) + np.abs(Y[iy, ix]-a[1])))
            cur = [round(float(X[iy[j], ix[j]]), 3), round(float(Y[iy[j], ix[j]]), 3)]; regs.append(cur)
        regs.reverse()
        while len(regs) < n:                         # keep the count: split the longest hop with a free site between
            pts = [a] + regs + [b]; hops = [md(u, v) for u, v in zip(pts, pts[1:])]; i = int(np.argmax(hops))
            u, v = pts[i], pts[i+1]; m = ok & (np.abs(X-u[0]) + np.abs(Y-u[1]) <= R) & (np.abs(X-v[0]) + np.abs(Y-v[1]) <= R)
            iy, ix = np.nonzero(m); j = int(np.argmin(np.abs(np.abs(X[iy, ix]-u[0]) + np.abs(Y[iy, ix]-u[1]) - hops[i]/2)))
            regs.insert(i, [round(float(X[iy[j], ix[j]]), 3), round(float(Y[iy[j], ix[j]]), 3)])
        after = worst([a] + regs + [b]); assert after <= GATE, (tn, e["conn"], after)
        e["regs_um"] = regs
        if len(regs) == n:
            out["kept"] += 1; e["note"] += f"; QUAD-8 min-hop street re-place (count kept {n}; wire over cores on M6/M7): worst {before:.1f} -> {after:.1f}"
        else:
            e["note"] += f"; QUAD-8 +1 station register (COORD quad-7 ruling; {n}->{n+1}, +1 cycle, TOK-HBM priced; wire over cores M6/M7): worst {before:.1f} -> {after:.1f}"
            out["added"].append(dict(type=tn, conn=e["conn"], launch=e["launch"], capture=e["capture"], bits=e["bits"],
                                     regs_before=n, regs_after=n+1, worst_before=round(before, 1), worst_after=round(after, 1), method="min-hop"))
        print(tn, e["conn"][:70], n, "->", len(regs), round(before, 1), "->", round(after, 1), flush=True)
(d / "die_plan.json").write_text(json.dumps(p, indent=1) + "\n")
rp["step2_min_hop"] = out
rp["added_one_reg"] += out["added"]; rp["added_chains"] = len(rp["added_one_reg"]); rp["added_bits_x_cycles"] = sum(x["bits"] for x in rp["added_one_reg"])
rp["still_failing"] = out["failing"]
(d / "relax_route_report.json").write_text(json.dumps(rp, indent=1) + "\n")
print("step2 kept", out["kept"], "added", len(out["added"]), "failing", out["failing"], "total added", rp["added_chains"])
