#!/usr/bin/env python3
"""tap_resolve.py: re-solve a partition type's explicit clock taps on its PLACED register inventory (die-agnostic).

FABLE-FIX-S81-LEPE 11-19.  Class (S81 lepe LP x2, seqhost, lepw LP; also bk_sel, kv_leaf): an explicit tap table solved on
the planned face / ft sinks leaves the interior registers on whichever tap is nearest, so the local trees of one type end
at very different insertions (lepe_mu_LP__t2: tap means 221..532 ps against a 250 ps target) and flop pairs a few um apart
on different taps carry that difference as hold and setup skew.

CRITERION (what decides, and what the solver drives down).  NOT the sink count of a tap: a type whose registers nearly all
sit on ONE tap is one balanced tree (QC sle_hc0, 13,082 sinks on one tap, closes).  The failure is the SPREAD of the mean
insertion between the taps that each clock a material share of the registers:
    spread = max - min of the per-tap mean insertion over taps with >= --min-share (1 %) of the registers
    verdict SPLIT when spread > --tol-ps (default: plan clock.neighbour_skew_ps, else 80).
The per-tap means are MEASURED when a kit CTS log is given (--cts-log: the last OT_TAP_BALANCE line); without one they are
a PREDICTION from the nearest-tap split (levels of a fanout tree + p95 wire), good for ranking only and printed as such.

SOLVER (clock.tap_mode explicit: append to clock.taps; grid+explicit: append to clock.added_taps).  Existing taps keep name and xy (collector / relay tap indexes stay valid); taps are only APPENDED.  The per-tap
load target is the largest load of a tap that already meets the insertion band in the measurement (at least 0.8 x
tap_max_sinks), so the added trees have the depth of the trees that work.  A tap is split while its load is over the
target, or while >= FAR_MIN of its sinks are beyond --radius-um; a new tap goes to the median of the far half, legalised
by the explicit-table rules (outline, tap_clear halo of hard cores, placed macros and keepouts, tap spacing), then all
added taps relax to the medians of their sinks.  A split that does not reduce the total excess is undone.

Register dump: `openroad -python tap_resolve.py --dump` with env ODB, OUT (cells: [name, x0, y0, x1, y1, master],
macros, outline; um), the format of taps.py bins.
"""
import json, math, os, re, statistics as st, sys

FAR_MIN = 60
STEP_UM = 2.16
REG_PREFIX = ("DFF", "ICG", "SDF", "DHL", "DLL")


def dump_odb(odb_path, out_path):
    import odb
    db = odb.dbDatabase.create()
    odb.read_db(db, odb_path)
    blk = db.getChip().getBlock()
    u = float(blk.getDbUnitsPerMicron())
    cells, macros = [], []
    for i in blk.getInsts():
        m = i.getMaster(); n = m.getName(); bb = i.getBBox()
        r = [i.getName(), bb.xMin() / u, bb.yMin() / u, bb.xMax() / u, bb.yMax() / u, n]
        if m.isBlock():
            macros.append(r)
        elif n.startswith(REG_PREFIX):
            cells.append(r)
    d = blk.getDieArea()
    json.dump({"outline": [d.xMin() / u, d.yMin() / u, d.xMax() / u, d.yMax() / u], "cells": cells, "macros": macros},
              open(out_path, "w"))
    print("TAP_RESOLVE_DUMP", len(cells), "registers", len(macros), "macros")


def parse_cts_log(text):
    """{tap: (mean_ps, min_ps, max_ps, sinks)} of the LAST OT_TAP_BALANCE iteration line (after the delay-chain pads)."""
    last = None
    for ln in text.splitlines():
        if ln.startswith("OT_TAP_BALANCE it"):
            last = ln
    out = {}
    if last:
        for n, mean, lo, hi, k in re.findall(r"(\S+)=(-?[\d.]+)\((-?[\d.]+)-(-?[\d.]+),(\d+)\)", last):
            out[n] = (float(mean), float(lo), float(hi), int(k))
    return out


def assign(taps, pts):
    """nearest tap (Manhattan) of every point: list of index lists."""
    import numpy as np
    A = np.array(taps, dtype=float).reshape(-1, 2); P = np.array(pts, dtype=float).reshape(-1, 2)
    idx = np.empty(len(P), dtype=int)
    for i in range(0, len(P), 4096):
        c = P[i:i + 4096]
        idx[i:i + 4096] = (np.abs(c[:, None, 0] - A[None, :, 0]) + np.abs(c[:, None, 1] - A[None, :, 1])).argmin(axis=1)
    g = [[] for _ in taps]
    for i, k in enumerate(idx):
        g[k].append(i)
    return g


def tap_stats(taps, pts, radius):
    """per tap: (load, sinks beyond radius, p95 distance, max distance)."""
    out = []
    for (x, y), s in zip(taps, assign(taps, pts)):
        ds = sorted(abs(pts[i][0] - x) + abs(pts[i][1] - y) for i in s) or [0.0]
        out.append((len(s), sum(1 for v in ds if v > radius), ds[int(0.95 * (len(ds) - 1))], ds[-1]))
    return out


def predicted_ps(load, p95_um):
    """ranking model only (fit on S81 lepe_mu_LP__t2 att22 unpadded trees): fanout-tree levels + p95 wire."""
    return 20.0 * math.log2(max(load, 8) / 8.0) + 0.45 * p95_um


def criterion(means, loads, tol_ps, min_share=0.01):
    """means / loads: {tap: ps} / {tap: sinks}.  -> dict(verdict, spread_ps, taps considered, exposed sinks)."""
    total = sum(loads.values()) or 1
    mat = [t for t in means if loads.get(t, 0) >= min_share * total]
    if len(mat) < 2:
        return {"verdict": "OK", "spread_ps": 0.0, "material_taps": len(mat), "why": "one tap clocks the type: one tree"}
    v = [means[t] for t in mat]
    spread = max(v) - min(v)
    return {"verdict": "SPLIT" if spread > tol_ps else "OK", "spread_ps": round(spread, 1), "material_taps": len(mat),
            "slowest": max(mat, key=lambda t: means[t]), "fastest": min(mat, key=lambda t: means[t]), "tol_ps": tol_ps}


def make_legal(outline, clear, boxes):
    w, h = outline
    def legal(x, y, taken):
        e = 1e-8
        return (clear - e <= x <= w - clear + e and clear - e <= y <= h - clear + e
                and not any(abs(x - a) < clear - e and abs(y - b) < clear - e for a, b in taken)
                and not any(a + e < x < c - e and b + e < y < d - e for a, b, c, d in boxes))
    return legal


def legalize(x, y, taken, legal):
    x, y = round(round(x / STEP_UM) * STEP_UM, 4), round(round(y / STEP_UM) * STEP_UM, 4)
    if legal(x, y, taken):
        return x, y
    for r in range(1, 600):
        for i in range(-r, r + 1):
            for j in {-(r - abs(i)), r - abs(i)}:
                a, b = round(x + i * STEP_UM, 4), round(y + j * STEP_UM, 4)
                if legal(a, b, taken):
                    return a, b
    raise ValueError("tap_resolve: no legal tap site")


def solve(exist, pts, legal, target, radius, core=(), max_add=80, min_new=40):
    """exist: [(x, y)] kept taps; pts: [(x, y)] registers; -> added [(x, y)]."""
    exist = [tuple(map(float, p)) for p in exist]; core = list(core); added = []
    med = lambda idx, k: st.median(pts[i][k] for i in idx)

    def relax(n):
        nonlocal added
        for _ in range(n):
            g = assign(exist + added, pts); new = []
            for k, xy in enumerate(added):
                s = g[len(exist) + k]
                new.append(legalize(med(s, 0), med(s, 1), exist + core + new + added[k + 1:], legal) if s else xy)
            added = new

    def excess(s_):
        return sum(max(0, n - target) for n, _, _, _ in s_) + sum(f for _, f, _, _ in s_ if f >= FAR_MIN)

    fails = 0
    while len(added) < max_add and fails < 6:
        T = exist + added; g = assign(T, pts); s_ = tap_stats(T, pts, radius)
        sc = [max(n / target, 1.0 + f / FAR_MIN if f >= FAR_MIN else 0.0) for n, f, _, _ in s_]
        order = sorted(range(len(T)), key=lambda i: -sc[i])
        k = order[min(fails, len(order) - 1)]
        if sc[k] <= 1.0:
            break
        s = g[k]; x, y = T[k]; n, f = s_[k][0], s_[k][1]
        if f >= FAR_MIN and 1.0 + f / FAR_MIN >= n / target:
            far = [i for i in s if abs(pts[i][0] - x) + abs(pts[i][1] - y) > radius]
        else:
            ax = 0 if (max(pts[i][0] for i in s) - min(pts[i][0] for i in s)) >= (max(pts[i][1] for i in s) - min(pts[i][1] for i in s)) else 1
            m = med(s, ax)
            lo = [i for i in s if pts[i][ax] <= m]; hi = [i for i in s if pts[i][ax] > m]
            cen = lambda q: abs(med(q, 0) - x) + abs(med(q, 1) - y) if q else -1.0
            far = hi if cen(hi) >= cen(lo) else lo
        keep = list(added); before = excess(s_)
        added.append(legalize(med(far, 0), med(far, 1), exist + core + added, legal))
        relax(2)
        s2 = tap_stats(exist + added, pts, radius)
        if excess(s2) >= before or min(q[0] for q in s2[len(exist):]) < min_new:
            added = keep; fails += 1
        else:
            fails = 0
    relax(3)
    return added


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan"); ap.add_argument("type")
    ap.add_argument("--regs", required=True, help="register dump JSON (--dump)")
    ap.add_argument("--cts-log", help="kit 4_1_cts.log: measured per-tap insertion")
    ap.add_argument("--target", type=int); ap.add_argument("--radius-um", type=float)
    ap.add_argument("--tol-ps", type=float); ap.add_argument("--min-share", type=float, default=0.01)
    ap.add_argument("--max-add", type=int, default=80); ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args(argv)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import schema, taps
    from placement_obstacles import placement_boxes
    P = schema.Plan(schema.load(a.plan), a.plan)
    t = P.types[a.type]; ck = t.get("clock", {})
    mode = ck.get("tap_mode", "grid")
    if mode not in ("explicit", "grid+explicit"):
        raise SystemExit(f"tap_resolve: type {a.type} clock.tap_mode is {mode!r}; taps are appended to explicit (clock.taps) or grid+explicit (clock.added_taps) tables only")
    clear = schema.type_tap_clear(t)
    d = json.load(open(a.regs))
    boxes = list(placement_boxes(t, halo=clear).values()) + [(x0 - clear, y0 - clear, x1 + clear, y1 + clear) for x0, y0, x1, y1 in ck.get("keepouts_um", [])]
    boxes += [(m[1] - clear, m[2] - clear, m[3] + clear, m[4] + clear) for m in d.get("macros", [])]
    legal = make_legal(t["outline_um"], clear, boxes)
    ex = taps.explicit_tap_sites(P, a.type) if mode == "explicit" else taps.grid_explicit_sites(P, a.type)
    names = [n for n, _, _ in ex]; exist = [(x, y) for _, x, y in ex]
    core = [(x, y) for _, x, y, _ in schema.core_taps(P, a.type)]
    pts = [((c[1] + c[3]) / 2, (c[2] + c[4]) / 2) for c in d["cells"]]
    cap = int(ck.get("tap_max_sinks", 1500)); radius = a.radius_um or 160.0
    ins = float(ck.get("insertion_ps", P.raw.get("clock", {}).get("insertion_ps", 250)))
    band = float(P.raw.get("clock", {}).get("insertion_tol_ps", 40))
    tol = a.tol_ps if a.tol_ps is not None else float(P.raw.get("clock", {}).get("neighbour_skew_ps", 80))
    s0 = tap_stats(exist, pts, radius)
    meas = parse_cts_log(open(a.cts_log, errors="replace").read()) if a.cts_log else {}
    if meas:
        means = {n: meas[n][0] for n in names if n in meas}; loads = {n: meas[n][3] for n in names if n in meas}; basis = "MEASURED"
    else:
        means = {n: predicted_ps(q[0], q[2]) for n, q in zip(names, s0)}; loads = {n: q[0] for n, q in zip(names, s0)}; basis = "PREDICTED"
    crit = criterion(means, loads, tol, a.min_share); crit["basis"] = basis
    ok_loads = [meas[n][3] for n in meas if n in names and meas[n][0] <= ins + band and meas[n][3] > 1]
    target = a.target or max(int(0.8 * cap), min(cap, max(ok_loads)) * 14 // 15 if ok_loads else 0)
    print(f"TAP_RESOLVE {a.type}: {len(pts)} registers, {len(exist)} taps, criterion {basis} spread {crit['spread_ps']} ps over {crit['material_taps']} material taps "
          f"(tol {tol}) -> {crit['verdict']}; target {target} sinks/tap, radius {radius} um")
    added = solve(exist, pts, legal, target, radius, core, a.max_add) if crit["verdict"] == "SPLIT" else []
    T = exist + added; s1 = tap_stats(T, pts, radius)
    allnames = names + [f"clk_t{len(exist) + i}" for i in range(len(added))]
    after = criterion({n: predicted_ps(q[0], q[2]) for n, q in zip(allnames, s1)}, {n: q[0] for n, q in zip(allnames, s1)}, tol, a.min_share)
    for n, (x, y), q in zip(allnames, T, s1):
        m = f" measured {means[n]:.0f} ps" if basis == "MEASURED" and n in means else ""
        print(f"  {n:8s} ({x:8.2f},{y:8.2f}) sinks {q[0]:6d} beyond-radius {q[1]:5d} p95 {q[2]:5.0f} um{m}{'  ADDED' if n not in names else ''}")
    print(f"TAP_RESOLVE {a.type}: added {len(added)}, max load {max(q[0] for q in s1)}, sinks beyond radius {sum(q[1] for q in s1)}, predicted spread after {after['spread_ps']} ps")
    json.dump({"schema": "opentallas.tap_resolve.v1", "type": a.type, "plan": a.plan, "regs": a.regs, "registers": len(pts), "criterion": crit,
               "predicted_after": after, "target_sinks": target, "radius_um": radius, "append_to": "clock.taps" if mode == "explicit" else "clock.added_taps",
               "added_taps": [{"name": f"clk_t{len(exist) + i}", "xy": [x, y]} for i, (x, y) in enumerate(added)],
               "load": {n: q[0] for n, q in zip(allnames, s1)}}, open(a.out, "w"), indent=1)
    return 0


if __name__ == "__main__":
    if "--dump" in sys.argv:
        dump_odb(os.environ["ODB"], os.environ["OUT"])
    else:
        sys.exit(main())
