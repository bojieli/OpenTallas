#!/usr/bin/env python3
"""Coarse hub global-route SCREEN (S81-AGGRO 2026-10-15): maze-routes every hub flow, field tree trunk, die link and the
SW service bundle through the rm5 hub on a gcell grid with the hub blocks as hard blockages (cluster rule: signals <= M6
inside the parents, so no over-the-block routing), and reports gcell-edge utilisation / overflow.

NOT OpenROAD GRT: a planning screen with the same capacity convention as hub_vm_centred.py (H edges M4+M6 36.46 t/um,
V edges M3+M5 48.61 t/um, minus 10 % for PG/clock), bundles of <= BUNDLE bits routed one by one with a negotiated
congestion cost (cost grows past 0.5 utilisation, steeply past 1.0).  Field trees: the 12 collect / 2 broadcast trees of
results/arch/s81_globalfp_1015/graph.json over the rm5_p1973 root placement (hub_shape_sweep.place), one trunk per
hub side, entering the hub boundary at the nearest root port.  Links lk_W*/lk_E* (1,027 b) enter at their y.
"""
from __future__ import annotations

import argparse
import heapq
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import hub_vm_centred as V  # noqa: E402

G = 86.4
BUNDLE = 256
PGF = 0.90
CAP_H = G * V.T_EW * PGF
CAP_V = G * V.T_NS * PGF
Y0, Y1 = 0.0, 26000.0


def grid_dims():
    nx = int(math.ceil((V.HUB[1] - V.HUB[0]) / G))
    ny = int(math.ceil((Y1 - Y0) / G))
    return nx, ny


def cell(x, y, nx, ny):
    return min(nx - 1, max(0, int((x - V.HUB[0]) / G))), min(ny - 1, max(0, int((y - Y0) / G)))


def blocked_cells(rects, nx, ny):
    blk = set()
    obst = list(rects.values()) + [b for b in FIX.values()]
    for (x, y, w, h) in obst:
        i0, j0 = cell(x + G / 2, y + G / 2, nx, ny)
        i1, j1 = cell(x + w - G / 2, y + h - G / 2, nx, ny)
        for i in range(i0, i1 + 1):
            for j in range(j0, j1 + 1):
                blk.add((i, j))
    return blk


def face_points(r, f, n, nx, ny, blk):
    """n pin cells just outside face f of r, spread along it, skipping blocked cells"""
    x, y, w, h = r
    pts = []
    for k in range(n):
        t = (k + 0.5) / n
        if f == "N":
            p = (x + t * w, y + h + G / 2)
        elif f == "S":
            p = (x + t * w, y - G / 2)
        elif f == "W":
            p = (x - G / 2, y + t * h)
        else:
            p = (x + w + G / 2, y + t * h)
        c = cell(*p, nx, ny)
        if c in blk:      # walk outward until free
            dx, dy = dict(N=(0, 1), S=(0, -1), W=(-1, 0), E=(1, 0))[f]
            for _ in range(40):
                c = (min(nx - 1, max(0, c[0] + dx)), min(ny - 1, max(0, c[1] + dy)))
                if c not in blk:
                    break
        pts.append(c)
    return pts


def nearest_face(ra, rb):
    ca = (ra[0] + ra[2] / 2, ra[1] + ra[3] / 2)
    best = None
    for f in "NSWE":
        (x0, y0), (x1, y1) = V.face_seg(rb, f)
        m = ((x0 + x1) / 2, (y0 + y1) / 2)
        d = abs(m[0] - ca[0]) + abs(m[1] - ca[1])
        if best is None or d < best[0]:
            best = (d, f)
    return best[1]


def field_bundles(L):
    """tree trunks + links + service: (src cells, dst block, dst face, bits, tag)"""
    import hub_shape_sweep as H
    sh = H.strip(5, False)
    pl = H.place(sh, 1973, False)
    ports = {p["root"]: (p["x"] + p["w"] / 2, p["y"] + p["h"] / 2, "W" if p["x"] < V.HUB[0] else "E") for p in pl["placements"]}
    out = []
    for t in H.trees():
        sides = {}
        for r in t["roots"]:
            sides.setdefault(ports[r][2], []).append(ports[r][1])
        for s, ys in sides.items():
            y = sorted(ys)[len(ys) // 2]          # trunk enters at the median root height of that side
            x = V.HUB[0] + G / 2 if s == "W" else V.HUB[1] - G / 2
            if t["kind"] == "collect":
                out.append(((x, y), "gather", "W" if s == "W" else "E", t["width"], f"collect-{s}"))
            else:
                out.append(((x, y), "pq", "W", t["width"], f"bcast-{s}"))
    for n in ("lk_W0", "lk_W1", "lk_W2", "lk_W3", "lk_E0", "lk_E1", "lk_E2", "lk_E3"):
        b = H.BOX[n]
        x = V.HUB[0] + G / 2 if n[3] == "W" else V.HUB[1] - G / 2
        out.append(((x, b[1] + b[3] / 2), "collective", None, 1027, "link"))
    out.append(((V.HUB[0] + G / 2, 3041.256 + 300.0), "vm", "svc", H.SVC_BITS, "svc"))
    return out


def route(L, fl_rows):
    global FIX
    FIX = V.fixed_for(L)
    nx, ny = grid_dims()
    R = L["rects"]
    blk = blocked_cells(R, nx, ny)
    use = {}
    nets = []
    for f in fl_rows:
        if f["direct"] and f["gap_um"] <= 100.0 or f.get("face_b") == "L-seam":
            continue           # abutting pin-to-pin (or reserved seam): no gcell route
        a, b = f["a"], f["b"]
        fa = f["face_a"]
        fb = f["face_b"] if f["face_b"] in "NSWE" and len(f["face_b"]) == 1 else nearest_face(R[a], R[b])
        nb = max(1, math.ceil(f["bits"] / BUNDLE))
        if f["direct"]:          # pins on both faces across the facing overlap window only
            ov, gp = V.facing(R[a], fa, R[b])
            segs = V.blocked(ov, fa, R[a], gp, R, {a, b}, segments=True)
            ov = max(segs, key=lambda q: q[1] - q[0])
            def clip(r, f_, lo=ov[0], hi=ov[1]):
                x, y, w, h = r
                return (lo, y, hi - lo, h) if f_ in "NS" else (x, lo, w, hi - lo)
            sa = face_points(clip(R[a], fa), fa, nb, nx, ny, blk)
            sb = face_points(clip(R[b], fb), fb, nb, nx, ny, blk)
        else:
            sa = face_points(R[a], fa, nb, nx, ny, blk)
            sb = face_points(R[b], fb, nb, nx, ny, blk)
        for k in range(nb):
            nets.append((f["bits"] / nb, sa[k], sb[k], f["name"]))
    for (x, y), b, fb, bits, tag in field_bundles(L):
        rb = R[b]
        if fb == "svc" and L.get("svc_face"):
            fb = L["svc_face"]
        elif fb == "svc":          # SW service enters the VM S face part not covered by the SU
            su = R["su"]
            lo = max(rb[0], su[0] + su[2]) if su[0] + su[2] < rb[0] + rb[2] and su[1] + su[3] <= rb[1] + 1 else rb[0]
            fb, rb = "S", (lo, rb[1], rb[0] + rb[2] - lo, rb[3])
        fb = fb or nearest_face((x, y, 0, 0), rb)
        nb = max(1, math.ceil(bits / BUNDLE))
        sb = face_points(rb, fb, nb, nx, ny, blk)
        s = cell(x, y, nx, ny)
        for k in range(nb):
            nets.append((bits / nb, s, sb[k], tag))
    nets.sort(key=lambda n: -abs(n[1][0] - n[2][0]) - abs(n[1][1] - n[2][1]))
    lens = {}
    for it in range(2):            # route, then rip-up-and-reroute once with history
        if it:
            use = {}
        for bits, s, t, tag in nets:
            path = astar(s, t, nx, ny, blk, use, bits)
            for e in path:
                use[e] = use.get(e, 0.0) + bits
            if it:
                lens.setdefault(tag, []).append(len(path) * G)
    return use, nx, ny, blk, lens


def cap(e):
    return CAP_H if e[2] == "h" else CAP_V


def astar(s, t, nx, ny, blk, use, bits):
    def h(c):
        return abs(c[0] - t[0]) + abs(c[1] - t[1])
    dist = {s: 0.0}
    prev = {}
    pq = [(h(s), 0.0, s)]
    while pq:
        _, d, c = heapq.heappop(pq)
        if c == t:
            break
        if d > dist.get(c, 1e18):
            continue
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (c[0] + dx, c[1] + dy)
            if not (0 <= n[0] < nx and 0 <= n[1] < ny) or (n in blk and n != t):
                continue
            e = (min(c[0], n[0]), min(c[1], n[1]), "h" if dx else "v")
            u = (use.get(e, 0.0) + bits) / cap(e)
            w = 1.0 + (0 if u < 0.5 else 4 * (u - 0.5)) + (0 if u < 1.0 else 50 * (u - 1.0))
            nd = d + w
            if nd < dist.get(n, 1e18):
                dist[n] = nd
                prev[n] = (c, e)
                heapq.heappush(pq, (nd + h(n), nd, n))
    path = []
    c = t
    while c != s and c in prev:
        c, e = prev[c]
        path.append(e)
    return path


def summarise(use):
    us = [v / cap(e) for e, v in use.items()]
    ov = sum(max(0.0, v - cap(e)) for e, v in use.items())
    return dict(edges_used=len(us), max_util=round(max(us), 3), p99_util=round(sorted(us)[int(0.99 * len(us))], 3),
                edges_over_060=sum(u > 0.60 for u in us), edges_over_100=sum(u > 1.0 for u in us),
                overflow_tracks=round(ov), overflow_edges=sum(u > 1.0 for u in us))


def render(L, use, nx, ny, blk, png, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    m = np.zeros((ny, nx))
    for e, v in use.items():
        i, j, _ = e
        m[j, i] = max(m[j, i], v / cap(e))
    fig, ax = plt.subplots(figsize=(6.5, 12))
    ext = [V.HUB[0] / 1e3, (V.HUB[0] + nx * G) / 1e3, Y0 / 1e3, (Y0 + ny * G) / 1e3]
    im = ax.imshow(np.ma.masked_where(m == 0, m), origin="lower", extent=ext, cmap="turbo", vmin=0, vmax=1.0,
                   interpolation="nearest")
    for k, (x, y, w, h) in L["rects"].items():
        ax.add_patch(plt.Rectangle((x / 1e3, y / 1e3), w / 1e3, h / 1e3, fill=True, fc="#cccccc", ec="k", lw=0.6))
        ax.text((x + w / 2) / 1e3, (y + h / 2) / 1e3, k, ha="center", va="center", fontsize=7)
    for k, (x, y, w, h) in V.fixed_for(L).items():
        ax.add_patch(plt.Rectangle((x / 1e3, y / 1e3), w / 1e3, h / 1e3, fill=True, fc="#eee8d5", ec="#888", lw=0.5))
    ax.set_xlim(ext[0], ext[1])
    ax.set_ylim(0, 26)
    ax.set_title(title, fontsize=9)
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    fig.colorbar(im, ax=ax, fraction=0.04, label="gcell-edge utilisation")
    fig.tight_layout()
    fig.savefig(png, dpi=110)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--png-dir", type=Path, required=True)
    a = ap.parse_args()
    a.png_dir.mkdir(parents=True, exist_ok=True)
    res = []
    for L in V.layouts():
        if L["key"] == "vmsq":
            continue           # needs a >= 12.7-mm hub (not rm5)
        ev = V.evaluate(L)
        use, nx, ny, blk, lens = route(L, ev["flows"])
        s = summarise(use)
        s.update(name=L["name"], key=L["key"], gcell_um=G, bundle_bits=BUNDLE,
                 max_len_um={k: round(max(v)) for k, v in lens.items()},
                 hub_hops={k: math.ceil(max(v) / 500.0) for k, v in lens.items()})
        png = a.png_dir / f"hub_grt_{L['key']}.png"
        render(L, use, nx, ny, blk, png, f"{L['name']}: max {s['max_util']}, >0.60 {s['edges_over_060']}, "
                                         f"overflow {s['overflow_edges']}")
        s["png"] = str(png)
        res.append(s)
        print(json.dumps(s))
    a.out.write_text(json.dumps(dict(schema="opentallas.s81.hub_grt_screen.v1", scope="PLANNING SCREEN, not OpenROAD",
                                     results=res), indent=1) + "\n")


if __name__ == "__main__":
    main()
