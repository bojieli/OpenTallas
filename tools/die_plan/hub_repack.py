#!/usr/bin/env python3
"""MASTER-PLAN-R6 (COORD 13:05 RULING HBM-B1E (2)): hub re-pack mode of the shared master-plan generator.

Opt-in plan transform (a plan that is not passed through it is unchanged):

  1. OUTLINE SHRINKS (spec JSON): a hard-core module gets a smaller outline only when the spec says its macros fit
     (macro_fit true) AND its estimated std-cell fill of the free core area is <= 0.6 (12.7e margin).  Refused
     entries are recorded with the reason (COORD: hfd_ep_static / sfustore_hw stay until macros fit, bfqg only at
     fill <= 0.6).  The outline shrinks about the core centre (origin snapped to the 4.32 lattice); edge pins keep
     their edge and are scaled along it (order kept, >= min(original gap, 0.192 um) spacing); the plan centre clock
     entry (entries.json) moves to the new centre on the 4.32 lattice; type clock taps follow.
  2. HUB RE-PACK: the hard cores of each named hub type are re-placed on a REGULAR bay/core lattice inside the
     unchanged hub outline (face pins, buses and die-level geometry unchanged): K horizontal shelves in old-y order
     separated by full-width horizontal bay streets, each shelf a row of columns in old-x order separated by full-
     height vertical bay streets, columns stacking cores bottom-up with a street between; every origin and every
     street on the 4.32 lattice; street width = the largest of the candidate widths that fits, slack spread evenly.
     The partition clock/reset tap moves to the nearest street cross.
  3. STATION REGENERATION: every internal station of a re-packed type, and every station of any type with an
     endpoint on a shrunk core, is re-routed and its registers re-placed: endpoints that sit on a moved/shrunk core
     follow it; the route may run over cores (M6/M7 above the M5 core ceiling) but every station register sits in
     free street area (outside every core + 4.32 halo) with every hop <= reach (360 um, the internal station rule);
     candidate routes HV / VH / Z through each street, else a street-only A* route.  The register count is kept at
     the old count when the new route allows it (static schedule / latency unchanged); fewer is padded, more is
     reported as a latency change (lat package owner regenerates).

All numbers produced are plan geometry; they are UNCHECKED until an independent NUMBER-CHECK (12.9f).
"""
import argparse
import copy
import hashlib
import heapq
import json
import math
import os
import re
import shutil
from pathlib import Path

G = 4.32
HALO = 4.32
PIN_PITCH = 0.192
LANDING_REACH = 405.0


def r3(v):
    return round(float(v), 3)


def fl(v, q=G):
    return round(math.floor(v / q + 1e-9) * q, 4)


def ce(v, q=G):
    return round(math.ceil(v / q - 1e-9) * q, 4)


def sn(v, q=G):
    return round(round(v / q) * q, 4)


# ----------------------------------------------------------------------------------------------- outline shrinks
def shrink_decision(spec_row, fill_max=0.6):
    """(accepted, reason) for one shrink spec row {module, outline_um, est_fill, macro_fit}."""
    if not spec_row.get("macro_fit", False):
        return False, "macros do not fit the proposed outline (with 4.32 halo)"
    f = spec_row.get("est_fill")
    if f is None:
        return False, "no std-cell fill estimate"
    if f > fill_max + 1e-9:
        return False, f"std-cell fill {f} > {fill_max}"
    return True, "macros fit, fill <= %.2f" % fill_max


def map_local(pt, old, new, tol=0.5):
    """core-local point -> shrunk outline: points on an edge keep that edge, others scale."""
    (x, y), (W, H), (W2, H2) = pt, old, new
    if x <= tol:
        x2 = x
    elif x >= W - tol:
        x2 = W2 - (W - x)
    else:
        x2 = x * W2 / W
    if y <= tol:
        y2 = y
    elif y >= H - tol:
        y2 = H2 - (H - y)
    else:
        y2 = y * H2 / H
    return (x2, y2)


def remap_pins(pins, old, new, tol=0.5):
    """pins [{name, layer, x, y}] on the edges of `old` -> `new`; per edge order kept, spacing >=
    min(original gap, PIN_PITCH); raises ValueError if an edge cannot hold its pins."""
    W, H = old
    W2, H2 = new
    out = [dict(p) for p in pins]
    edges = {"S": [], "N": [], "W": [], "E": [], "in": []}
    for i, p in enumerate(out):
        x, y = p["x"], p["y"]
        if y <= tol:
            edges["S"].append(i)
        elif y >= H - tol:
            edges["N"].append(i)
        elif x <= tol:
            edges["W"].append(i)
        elif x >= W - tol:
            edges["E"].append(i)
        else:
            edges["in"].append(i)
    for e, idx in edges.items():
        if e == "in":
            for i in idx:
                x2, y2 = map_local((out[i]["x"], out[i]["y"]), old, new, tol)
                out[i]["x"], out[i]["y"] = round(x2, 3), round(y2, 3)
            continue
        along = "x" if e in ("S", "N") else "y"
        L, L2 = (W, W2) if along == "x" else (H, H2)
        idx = sorted(idx, key=lambda i: (out[i][along], out[i]["layer"]))
        by_layer = {}
        for i in idx:
            by_layer.setdefault(out[i]["layer"], []).append(i)
        for lay, ii in by_layer.items():
            orig = [pins[i][along] for i in ii]
            prev = None
            for k, i in enumerate(ii):
                v = orig[k] * L2 / L
                if prev is not None:
                    need = min(orig[k] - orig[k - 1], PIN_PITCH)
                    v = max(v, prev + need)
                prev = v
                out[i][along] = round(v, 3)
            if ii and out[ii[-1]][along] > L2 - 0.0:
                raise ValueError(f"edge {e} layer {lay}: {len(ii)} pins do not fit {L2} um")
        for i in idx:
            x, y = out[i]["x"], out[i]["y"]
            if e == "N":
                out[i]["y"] = round(H2 - (H - pins[i]["y"]), 3)
            elif e == "E":
                out[i]["x"] = round(W2 - (W - pins[i]["x"]), 3)
    return out


# ----------------------------------------------------------------------------------------------- hub packing
def _pack_shelf(cores, sh, lane):
    """cores (sorted by old cx) -> columns [{w, c:[core]}] stacked bottom-up with `lane` between (<= sh)."""
    cols = []
    for c in sorted(cores, key=lambda c: c["ocx"]):
        w, h = ce(c["w"]), ce(c["h"])
        if cols:
            col = cols[-1]
            top = sum(ce(q["h"]) for q in col["c"]) + lane * len(col["c"])
            if top + h <= sh + 1e-6 and w <= col["w"] + 1e-6:
                col["c"].append(c)
                continue
        cols.append(dict(w=w, c=[c]))
    return cols, lane + sum(col["w"] + lane for col in cols)


def pack_hub(W, H, cores, lanes=(51.84, 43.2, 34.56, 25.92, 17.28), shelves=(2, 3, 4), conns=None, reach=360.0):
    """regular shelf/column/stack lattice.  cores: [{inst, w, h, ocx, ocy}] -> (placement {inst: (x, y)},
    info).  Search: widest street first, then (with conns) the fewest estimated added station registers
    (sum over stations of max(0, ceil(manhattan / reach) - 1 - n_old), endpoints following their cores), then
    the smallest total centre displacement (topology kept: shelves in old-y order, columns in old-x order).
    conns: [(end_a, end_b, n_old)], end = (inst, dx, dy) core-relative to the core origin or (None, x, y) fixed."""
    import itertools
    import numpy as np
    C = sorted(cores, key=lambda c: (c["ocy"], c["ocx"]))
    n = len(C)
    idx = {c["inst"]: i for i, c in enumerate(C)}
    if conns:
        ea = np.array([idx.get(a[0], -1) for a, b, _ in conns])
        eb = np.array([idx.get(b[0], -1) for a, b, _ in conns])
        oa = np.array([[a[1], a[2]] for a, b, _ in conns], dtype=float)
        ob = np.array([[b[1], b[2]] for a, b, _ in conns], dtype=float)
        nold = np.array([c[2] for c in conns], dtype=float)

    def extra_regs(place):
        if not conns:
            return 0.0
        org = np.array([place[c["inst"]] for c in C] + [(0.0, 0.0)], dtype=float)
        pa = oa + org[ea]
        pb = ob + org[eb]
        L = np.abs(pa - pb).sum(axis=1)
        return float(np.maximum(0.0, np.ceil(L / reach - 1e-9) - 1 - nold).sum())
    for lane in lanes:
        best = None
        for K in shelves:
            for cuts in itertools.combinations(range(1, n), K - 1):
                b = [0] + list(cuts) + [n]
                sh = [C[b[i]:b[i + 1]] for i in range(K)]
                hs = [ce(max(c["h"] for c in s)) for s in sh]
                if lane + sum(h + lane for h in hs) > H + 1e-6:
                    continue
                packed = [_pack_shelf(s, h, lane) for s, h in zip(sh, hs)]
                if max(p[1] for p in packed) > W + 1e-6:
                    continue
                place, streets = _realise(W, H, hs, packed, lane)
                disp = sum(abs(place[c["inst"]][0] + c["w"] / 2 - c["ocx"]) +
                           abs(place[c["inst"]][1] + c["h"] / 2 - c["ocy"]) for c in C)
                key = (extra_regs(place), disp)
                if best is None or key < best[0]:
                    best = (key, K, cuts, place, streets, hs)
            if K >= 3 and best is not None and n > 40:
                break                      # combinations grow fast; 2..3 shelves cover the hubs
        if best:
            (xr0, disp0), K, cuts, place, streets, hs = best
            b = [0] + list(cuts) + [n]
            shelf = {C[i]["inst"]: k for k in range(K) for i in range(b[k], b[k + 1])}
            xkey = {c["inst"]: c["ocx"] for c in C}

            def evaluate(shelf, xkey):
                sh = [[dict(c, ocx=xkey[c["inst"]]) for c in C if shelf[c["inst"]] == k] for k in range(K)]
                if any(not s_ for s_ in sh):
                    return None
                hs_ = [ce(max(c["h"] for c in s_)) for s_ in sh]
                if lane + sum(h + lane for h in hs_) > H + 1e-6:
                    return None
                packed = [_pack_shelf(s_, h, lane) for s_, h in zip(sh, hs_)]
                if max(p[1] for p in packed) > W + 1e-6:
                    return None
                pl, stv = _realise(W, H, hs_, packed, lane)
                d = sum(abs(pl[c["inst"]][0] + c["w"] / 2 - c["ocx"]) + abs(pl[c["inst"]][1] + c["h"] / 2 - c["ocy"])
                        for c in C)
                return (extra_regs(pl), d), pl, stv, hs_
            cur = evaluate(shelf, xkey)
            moves = 0
            for sweep in range(6 if conns else 0):     # local search: move one core to another shelf / x slot
                improved = False
                for c in C:
                    i = c["inst"]
                    trials = [(k, xkey[i]) for k in range(K) if k != shelf[i]]
                    trials += [(shelf[j], xkey[j] + e) for j in xkey if j != i for e in (-0.5, 0.5)]
                    for k, xk in trials:
                        s0, x0 = shelf[i], xkey[i]
                        shelf[i], xkey[i] = k, xk
                        r = evaluate(shelf, xkey)
                        if r is not None and r[0] < cur[0]:
                            cur = r
                            moves += 1
                            improved = True
                        else:
                            shelf[i], xkey[i] = s0, x0
                if not improved:
                    break
            (xr, disp), place, streets, hs = cur
            return place, dict(lane_um=lane, shelves=K, shelf_heights_um=[r3(h) for h in hs],
                               shelf_cuts_old_y_order=list(cuts), est_added_regs_initial=r3(xr0),
                               est_added_regs=r3(xr), local_search_moves=moves,
                               displacement_um_total=r3(disp), displacement_um_mean=r3(disp / n), streets=streets)
    raise ValueError("hub cores do not fit the outline on any street width")


def _realise(W, H, hs, packed, lane):
    K = len(hs)
    sy = H - sum(hs) - (K + 1) * lane
    gy = fl(lane + sy / (K + 1))
    place, hstreets, vstreets = {}, [], []
    y = gy
    hstreets.append([0.0, r3(gy)])
    for k, (cols, _) in enumerate(packed):
        nc = len(cols)
        sx = W - sum(c["w"] for c in cols) - (nc + 1) * lane
        gx = fl(lane + sx / (nc + 1))
        x = gx
        vstreets.append([r3(0.0), r3(y), r3(gx), r3(y + hs[k])])
        for col in cols:
            yy = y
            for c in col["c"]:
                place[c["inst"]] = (r3(x + fl((col["w"] - c["w"]) / 2)), r3(yy))
                yy = ce(yy + c["h"] + lane)
            x = r3(x + col["w"])
            vstreets.append([r3(x), r3(y), r3(min(W, x + gx)), r3(y + hs[k])])
            x = r3(x + gx)
        y = r3(y + hs[k])
        hstreets.append([r3(y), r3(min(H, y + gy))])
        y = r3(y + gy)
    return place, dict(horizontal_y_um=hstreets, vertical_rects_um=vstreets)


# ----------------------------------------------------------------------------------------------- station routing
class Raster:
    """free (outside every core + halo, inside the outline) on the 4.32 lattice of a partition type."""

    def __init__(self, W, H, rects, halo=HALO):
        import numpy as np
        self.W, self.H = W, H
        self.nx, self.ny = int(W / G) + 1, int(H / G) + 1
        f = np.ones((self.nx, self.ny), dtype=bool)
        for (x0, y0, x1, y1) in rects:
            i0, i1 = max(0, int(math.ceil((x0 - halo) / G - 1e-9))), min(self.nx - 1, int((x1 + halo) / G + 1e-9))
            j0, j1 = max(0, int(math.ceil((y0 - halo) / G - 1e-9))), min(self.ny - 1, int((y1 + halo) / G + 1e-9))
            if i0 <= i1 and j0 <= j1:
                f[i0:i1 + 1, j0:j1 + 1] = False
        self.f = f
        self.rects = rects

    def free(self, x, y):
        i, j = int(round(x / G)), int(round(y / G))
        return 0 <= i < self.nx and 0 <= j < self.ny and bool(self.f[i, j])

    def core_at(self, p, tol=0.5):
        for k, (x0, y0, x1, y1) in enumerate(self.rects):
            if x0 - tol <= p[0] <= x1 + tol and y0 - tol <= p[1] <= y1 + tol:
                return k
        return None


def escape(R, p, tol=0.5):
    """lattice point outside the halo of the core p sits on (perpendicular to its nearest edge); a face / free
    point snaps to the nearest free lattice point."""
    k = R.core_at(p, tol)
    if k is None:
        x, y = sn(p[0]), sn(p[1])
        if R.free(x, y):
            return (x, y)
        for d in range(1, 40):
            for dx, dy in ((d, 0), (-d, 0), (0, d), (0, -d)):
                if R.free(x + dx * G, y + dy * G):
                    return (x + dx * G, y + dy * G)
        return (x, y)
    x0, y0, x1, y1 = R.rects[k]
    d = {"W": p[0] - x0, "E": x1 - p[0], "S": p[1] - y0, "N": y1 - p[1]}
    order = sorted(d, key=d.get)
    for e in order:
        if e == "W":
            q = (fl(x0 - HALO - 0.01), sn(p[1]))
        elif e == "E":
            q = (ce(x1 + HALO + 0.01), sn(p[1]))
        elif e == "S":
            q = (sn(p[0]), fl(y0 - HALO - 0.01))
        else:
            q = (sn(p[0]), ce(y1 + HALO + 0.01))
        q = (min(max(q[0], 0.0), fl(R.W)), min(max(q[1], 0.0), fl(R.H)))
        if R.free(*q):
            return q
    return escape(R, (sn(p[0]), sn(p[1])), tol=-1)


def _samples(poly):
    """arc samples (s, x, y) every 4.32 along a lattice polyline."""
    out = [(0.0, poly[0][0], poly[0][1])]
    s = 0.0
    for a, b in zip(poly, poly[1:]):
        L = abs(b[0] - a[0]) + abs(b[1] - a[1])
        n = int(round(L / G))
        for k in range(1, n + 1):
            t = k / n
            out.append((s + L * t, a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
        s += L
    return out


def place_regs(R, poly, a_len, b_len, n_old, reach):
    """registers on free lattice samples of `poly` (escape-to-escape) with every hop <= reach; the pin stubs
    a_len / b_len count in the first / last hop.  Returns (regs [(x, y)], n_min) or (None, None)."""
    S = _samples(poly)
    L = S[-1][0]
    free = [(s, x, y) for s, x, y in S if R.free(x, y)]
    pos = -a_len
    end = L + b_len
    # an interior core pin farther than reach from every free street point: its landing hop may use the die plan
    # reach (12.1e, 405 um) instead of the internal-station margin (reported as landing_hops_over_reach)
    first = reach if a_len <= reach - 2 * G else LANDING_REACH
    last = reach if b_len <= reach - 2 * G else LANDING_REACH
    regs = []
    while True:
        fin = max(first, last) if not regs else last
        if end - pos <= fin + 1e-6:
            break
        lim = first if not regs else reach
        cand = [q for q in free if pos + 1e-6 < q[0] <= pos + lim + 1e-6]
        if not cand:
            return None, None
        q = cand[-1]
        regs.append(q)
        pos = q[0]
    n_min = len(regs)
    while len(regs) < n_old:                    # keep the old register count (static schedule unchanged)
        pts = [-a_len] + [q[0] for q in regs] + [end]
        gi = max(range(len(pts) - 1), key=lambda i: pts[i + 1] - pts[i])
        mid = (pts[gi] + pts[gi + 1]) / 2
        cand = [q for q in free if pts[gi] + G - 1e-6 <= q[0] <= pts[gi + 1] - G + 1e-6
                and all(abs(q[0] - r[0]) > 1e-6 for r in regs)]
        if not cand:
            break
        q = min(cand, key=lambda q: abs(q[0] - mid))
        regs.append(q)
        regs.sort()
    return [(r3(x), r3(y)) for _, x, y in regs], n_min


def astar(R, a, b, step=2):
    """street-only route (free cells, 8.64 steps) between lattice points a, b -> lattice polyline or None."""
    import numpy as np
    st = step
    nx, ny = R.nx, R.ny
    ai, aj = int(round(a[0] / G)), int(round(a[1] / G))
    bi, bj = int(round(b[0] / G)), int(round(b[1] / G))
    f = R.f
    start, goal = (ai, aj), (bi, bj)
    g = {start: 0}
    par = {start: None}
    hq = [(abs(ai - bi) + abs(aj - bj), 0, start)]
    seen = set()
    while hq:
        _, gc, u = heapq.heappop(hq)
        if u in seen:
            continue
        seen.add(u)
        if abs(u[0] - bi) + abs(u[1] - bj) <= st:
            path = [goal]
            while u is not None:
                path.append(u)
                u = par[u]
            pts = [(r3(i * G), r3(j * G)) for i, j in reversed(path)]
            out = [pts[0]]
            for p in pts[1:]:                        # make Manhattan + drop collinear points
                if p[0] != out[-1][0] and p[1] != out[-1][1]:
                    out.append((p[0], out[-1][1]))
                out.append(p)
            simp = [out[0]]
            for p in out[1:]:
                if len(simp) >= 2 and (simp[-2][0] == simp[-1][0] == p[0] or simp[-2][1] == simp[-1][1] == p[1]):
                    simp[-1] = p
                elif p != simp[-1]:
                    simp.append(p)
            return simp
        for di, dj in ((st, 0), (-st, 0), (0, st), (0, -st)):
            v = (u[0] + di, u[1] + dj)
            if not (0 <= v[0] < nx and 0 <= v[1] < ny) or not f[v[0], v[1]] or v in seen:
                continue
            ng = gc + st
            if ng < g.get(v, 1e18):
                g[v] = ng
                par[v] = u
                heapq.heappush(hq, (ng + abs(v[0] - bi) + abs(v[1] - bj), ng, v))
    return None


def route_station(R, a, b, n_old, reach, streets_y=(), streets_x=()):
    """(poly incl. pins, regs, n_min, kind) for pins a -> b."""
    ea, eb = escape(R, a), escape(R, b)
    la = abs(ea[0] - a[0]) + abs(ea[1] - a[1])
    lb = abs(eb[0] - b[0]) + abs(eb[1] - b[1])
    cands = [("HV", [ea, (eb[0], ea[1]), eb]), ("VH", [ea, (ea[0], eb[1]), eb])]
    for y in streets_y:
        cands.append(("Zy", [ea, (ea[0], y), (eb[0], y), eb]))
    lo, hi = min(ea[0], eb[0]) - 600, max(ea[0], eb[0]) + 600
    for x in streets_x:
        if lo <= x <= hi:
            cands.append(("Zx", [ea, (x, ea[1]), (x, eb[1]), eb]))
    best = None
    for kind, poly in cands:
        poly = [p for i, p in enumerate(poly) if i == 0 or p != poly[i - 1]]
        L = sum(abs(q[0] - p[0]) + abs(q[1] - p[1]) for p, q in zip(poly, poly[1:]))
        if best is not None and L >= best[0]:
            continue
        regs, n_min = place_regs(R, poly, la, lb, n_old, reach)
        if regs is None:
            continue
        best = (L, kind, poly, regs, n_min)
    if best is None:
        poly = astar(R, ea, eb)
        if poly is not None:
            regs, n_min = place_regs(R, poly, la, lb, n_old, reach)
            if regs is not None:
                L = sum(abs(q[0] - p[0]) + abs(q[1] - p[1]) for p, q in zip(poly, poly[1:]))
                best = (L, "astar", poly, regs, n_min)
    if best is None:
        return None
    L, kind, poly, regs, n_min = best
    return dict(length_um=r3(L + la + lb), kind=kind, regs=regs, n_min=n_min)


# ----------------------------------------------------------------------------------------------- driver
def _core_rect(h):
    x, y = h["origin_um"]
    w, hh = h["outline_um"]
    return (x, y, x + w, y + hh)


def _pin_file_name(old, module, w, h):
    m = re.match(r"(.*?/)?([^/]+?)__([0-9.]+)x([0-9.]+)__(.+)$", old)
    if not m:
        return None
    return f"{m.group(1) or ''}{module}__{w:g}x{h:g}__{m.group(5)}"


def run(plan_dir, out_dir, hub_types, shrink_spec=None, reach=360.0, fill_max=0.6, log=print):
    plan_dir, out_dir = Path(plan_dir), Path(out_dir)
    P = json.loads((plan_dir / "die_plan.json").read_text())
    entries = json.loads((plan_dir / "entries.json").read_text()) if (plan_dir / "entries.json").exists() else None
    T = P["partition_types"]
    _snapshot_old(P)
    rep = dict(schema="opentallas.hub_repack.v1", source_plan_sha256=hashlib.sha256(
        (plan_dir / "die_plan.json").read_bytes()).hexdigest(), reach_um=reach, shrinks=[], hubs={}, stations={})
    new_pin_files = {}
    # ---- 1. outline shrinks
    shrink = {}
    for row in (shrink_spec or []):
        ok, why = shrink_decision(row, fill_max)
        rep["shrinks"].append(dict(module=row["module"], outline_um=row["outline_um"], est_fill=row.get("est_fill"),
                                   macro_fit=row.get("macro_fit"), accepted=ok, reason=why))
        if ok:
            shrink[row["module"]] = tuple(row["outline_um"])
    maps = {}                     # (type, inst) -> f(type-frame point on the old core) -> new type-frame point
    touched = set()
    for tn, t in T.items():
        for h in t.get("hard_cores", []):
            if h["module"] not in shrink:
                continue
            old = tuple(h["outline_um"])
            new = shrink[h["module"]]
            if tuple(old) == tuple(new):
                continue
            ox, oy = h["origin_um"]
            nox = sn(ox + (old[0] - new[0]) / 2)
            noy = sn(oy + (old[1] - new[1]) / 2)
            pf = h.get("pins_file")
            if pf:
                pins = json.loads((plan_dir / pf).read_text())
                npins = remap_pins(pins, old, new)
                npf = _pin_file_name(pf, h["module"], new[0], new[1])
                new_pin_files[npf] = npins
                h["pins_file"] = npf
            h["note"] = (h.get("note", "") + f" | MASTER-PLAN-R6 outline shrink {old[0]}x{old[1]} -> "
                         f"{new[0]}x{new[1]} (centre kept, edge pins scaled)").strip(" |")
            h["outline_um"] = [new[0], new[1]]
            h["origin_um"] = [nox, noy]
            maps[(tn, h["inst"])] = (lambda p, ox=ox, oy=oy, old=old, new=new, nox=nox, noy=noy:
                                     tuple(v + o for v, o in zip(map_local((p[0] - ox, p[1] - oy), old, new),
                                                                 (nox, noy))))
            touched.add(tn)
            if entries is not None:
                entries[h["module"]] = dict(source="master plan centre entry on the 4.32 PG lattice (12.8a, "
                                                   "MASTER-PLAN-R6 shrunk outline)",
                                            xy=[sn(new[0] / 2), sn(new[1] / 2)])
    # ---- 2. hub re-pack
    for tn in hub_types:
        t = T[tn]
        W, H = t["outline_um"]
        cores = [dict(inst=h["inst"], w=h["outline_um"][0], h=h["outline_um"][1],
                      ocx=h["origin_um"][0] + h["outline_um"][0] / 2, ocy=h["origin_um"][1] + h["outline_um"][1] / 2)
                 for h in t["hard_cores"]]
        conns = []
        for st in t.get("internal_stations", []):
            ends = []
            for p in (st["from_um"], st["to_um"]):
                q = _follow(tn, tuple(p), maps, _OLD[tn])          # shrink map first (core origin unchanged)
                inst = next((i for i, r in _OLD[tn].items()
                             if r[0] - 0.5 <= p[0] <= r[2] + 0.5 and r[1] - 0.5 <= p[1] <= r[3] + 0.5), None)
                if inst is None:
                    ends.append((None, q[0], q[1]))
                else:
                    h = next(h for h in t["hard_cores"] if h["inst"] == inst)
                    ends.append((inst, q[0] - h["origin_um"][0], q[1] - h["origin_um"][1]))
            conns.append((ends[0], ends[1], len(st.get("regs_um", []))))
        place, info = pack_hub(W, H, cores, conns=conns, reach=reach)
        for h in t["hard_cores"]:
            x, y = place[h["inst"]]
            dx, dy = x - h["origin_um"][0], y - h["origin_um"][1]
            prev = maps.get((tn, h["inst"]))
            maps[(tn, h["inst"])] = (lambda p, prev=prev, dx=dx, dy=dy:
                                     tuple(v + d for v, d in zip(prev(p) if prev else p, (dx, dy))))
            h["origin_um"] = [x, y]
        hs = info["streets"]["horizontal_y_um"]
        vs = info["streets"]["vertical_rects_um"]
        cross = [(sn((v[0] + v[2]) / 2), sn((y0 + y1) / 2)) for v in vs for (y0, y1) in hs
                 if abs(y0 - v[3]) < 1e-3 or abs(y1 - v[1]) < 1e-3]
        old_tap = t.get("clock", {}).get("tap_um")
        if old_tap and cross:
            nt = min(cross, key=lambda c: abs(c[0] - old_tap[0]) + abs(c[1] - old_tap[1]))
            t["clock"]["tap_um"] = [r3(nt[0]), r3(nt[1])]
            if t.get("reset", {}).get("tap_um"):
                t["reset"]["tap_um"] = [r3(nt[0]), r3(nt[1])]
            info["partition_tap_um"] = dict(old=old_tap, new=[r3(nt[0]), r3(nt[1])])
        t["note"] = (t.get("note", "") + f" | MASTER-PLAN-R6 hub re-pack: {info['shelves']} shelves, "
                     f"{info['lane_um']} um bay streets on the 4.32 lattice, stations regenerated").strip(" |")
        rep["hubs"][tn] = info
        touched.add(tn)
    # contents / clock taps follow the cores
    for tn in touched:
        t = T[tn]
        hc = {h["inst"]: h for h in t["hard_cores"]}
        for c in t.get("contents", []):
            if c.get("inst") in hc and "origin_um" in c:
                c["origin_um"] = list(hc[c["inst"]]["origin_um"])
                c["outline_um"] = list(hc[c["inst"]]["outline_um"])
        for tp in (t.get("clock") or {}).get("taps", []):
            inst = tp.get("name", "").split(".")[0]
            h = hc.get(inst)
            if h and entries is not None and h["module"] in entries:
                e = entries[h["module"]]["xy"]
                tp["xy"] = [r3(h["origin_um"][0] + e[0]), r3(h["origin_um"][1] + e[1])]
    # ---- 3. stations
    for tn in sorted(touched):
        t = T[tn]
        W, H = t["outline_um"]
        rects_new = [_core_rect(h) for h in t["hard_cores"]]
        R = Raster(W, H, rects_new)
        info = rep["hubs"].get(tn, {})
        sy = [sn((a + b) / 2) for a, b in info.get("streets", {}).get("horizontal_y_um", [])]
        sx = sorted({sn((v[0] + v[2]) / 2) for v in info.get("streets", {}).get("vertical_rects_um", [])})
        stats = dict(stations=0, regenerated=0, kept=0, regs_old=0, regs_new=0, latency_up=[], padded_short=[],
                     failed=[], kinds={})
        for k, st in enumerate(t.get("internal_stations", [])):
            stats["stations"] += 1
            a, b = tuple(st["from_um"]), tuple(st["to_um"])
            na, nb = _follow(tn, a, maps, _OLD[tn]), _follow(tn, b, maps, _OLD[tn])
            if tn not in hub_types and na == a and nb == b:
                stats["kept"] += 1
                stats["regs_old"] += len(st.get("regs_um", []))
                stats["regs_new"] += len(st.get("regs_um", []))
                continue
            n_old = len(st.get("regs_um", []))
            res = route_station(R, na, nb, n_old, reach, sy, sx)
            stats["regs_old"] += n_old
            if res is None:
                stats["failed"].append(dict(station=k, conn=st.get("conn"), from_um=list(na), to_um=list(nb)))
                st["from_um"], st["to_um"] = [r3(na[0]), r3(na[1])], [r3(nb[0]), r3(nb[1])]
                stats["regs_new"] += n_old
                continue
            stats["regenerated"] += 1
            stats["kinds"][res["kind"]] = stats["kinds"].get(res["kind"], 0) + 1
            stats["regs_new"] += len(res["regs"])
            if len(res["regs"]) > n_old:
                stats["latency_up"].append(dict(station=k, conn=st.get("conn"), regs_old=n_old,
                                                regs_new=len(res["regs"])))
            elif len(res["regs"]) < n_old:
                stats["padded_short"].append(dict(station=k, conn=st.get("conn"), regs_old=n_old,
                                                  regs_new=len(res["regs"])))
            st["from_um"], st["to_um"] = [r3(na[0]), r3(na[1])], [r3(nb[0]), r3(nb[1])]
            st["regs_um"] = [list(r) for r in res["regs"]]
            st["note"] = (f"MASTER-PLAN-R6 regenerated ({res['kind']}, {res['length_um']} um, {len(res['regs'])} "
                          f"station(s), hops <= {reach:g} um, registers in bay streets)")
        rep["stations"][tn] = stats
        log(f"{tn}: {stats['stations']} stations, {stats['regenerated']} regenerated, "
            f"regs {stats['regs_old']} -> {stats['regs_new']}, latency_up {len(stats['latency_up'])}, "
            f"short {len(stats['padded_short'])}, failed {len(stats['failed'])}")
    P["note"] = (P.get("note", "") + " | MASTER-PLAN-R6 hub re-pack (" + ", ".join(hub_types) + ") + outline "
                 "shrinks (" + ", ".join(sorted(shrink)) + ")").strip(" |")
    # ---- write the bundle (hard links for unchanged files)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    shutil.copytree(plan_dir, out_dir, copy_function=os.link, symlinks=True)
    for name in ("die_plan.json", "entries.json", "die_plan.sha256"):
        q = out_dir / name
        if q.exists():
            q.unlink()
    (out_dir / "die_plan.json").write_text(json.dumps(P, indent=1) + "\n")
    if entries is not None:
        (out_dir / "entries.json").write_text(json.dumps(entries, indent=1, sort_keys=True) + "\n")
    for npf, pins in new_pin_files.items():
        q = out_dir / npf
        if q.exists():
            q.unlink()
        q.write_text(json.dumps(pins) + "\n")
    sha = hashlib.sha256((out_dir / "die_plan.json").read_bytes()).hexdigest()
    (out_dir / "die_plan.sha256").write_text(f"{sha}  die_plan.json\n")
    rep["plan_sha256"] = sha
    rep["new_pin_files"] = sorted(new_pin_files)
    (out_dir / "hub_repack_report.json").write_text(json.dumps(rep, indent=1) + "\n")
    return rep


_OLD = {}


def _follow(tn, p, maps, old):
    """new position of a type-frame point: an endpoint on an old core rect follows that core's map."""
    for inst, r in old.items():
        if r[0] - 0.5 <= p[0] <= r[2] + 0.5 and r[1] - 0.5 <= p[1] <= r[3] + 0.5:
            f = maps.get((tn, inst))
            if f:
                q = f(p)
                return (r3(q[0]), r3(q[1]))
    return p


def _snapshot_old(P):
    for tn, t in P["partition_types"].items():
        _OLD[tn] = {h["inst"]: _core_rect(h) for h in t.get("hard_cores", [])}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan_dir")
    ap.add_argument("--out", required=True)
    ap.add_argument("--hubs", default="", help="comma list of hub partition types to re-pack")
    ap.add_argument("--shrink", help="JSON [{module, outline_um, est_fill, macro_fit, source}]")
    ap.add_argument("--reach-um", type=float, default=360.0)
    a = ap.parse_args(argv)
    spec = json.loads(Path(a.shrink).read_text()) if a.shrink else []
    rep = run(a.plan_dir, a.out, [h for h in a.hubs.split(",") if h], spec, a.reach_um)
    print(json.dumps({k: v for k, v in rep.items() if k in ("plan_sha256", "shrinks")}, indent=1))


if __name__ == "__main__":
    main()
