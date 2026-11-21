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

SINK REGION RULE (COORD 11-19: tap sink region W + H <= 300 um, no spill; --span-um 300).  The sink region of a tap is the
bounding box of the registers it takes in the nearest-tap split.  With --span-um the solver also splits every tap whose
region has W + H over the limit, at the geometric middle of the longer side (the half away from the tap gets the new tap),
and taps of a few sinks are allowed (--min-new, default 8 in this mode): far stragglers get their own tap instead of
spilling into a neighbour's region.  The report prints each tap's W + H and the count of taps still over the limit.

Register dump: `openroad -python tap_resolve.py --dump` with env ODB, OUT (cells: [name, x0, y0, x1, y1, master],
macros, outline; um), the format of taps.py bins.  clock_root[i] (TAP-GRID-R3) = the block input port whose net clocks
cells[i], traced through buffers / inverters / ICGs (trace_root); `taps.py bins --tap-net` keeps only the tap-net ones.
"""
import json, math, os, re, statistics as st, sys

FAR_MIN = 60
STEP_UM = 2.16
REG_PREFIX = ("DFF", "ICG", "SDF", "DHL", "DLL")


CLOCK_PIN_NAMES = ("CLK", "CK", "CLKN", "GCLK_IN")
ROOT_MAX_DEPTH = 64


def trace_root(start, upstream, max_depth=ROOT_MAX_DEPTH):
    """clock root of a register clock pin, following its net upstream (TAP-GRID-R3 11-21, COORD ruling: a tap's load is
    the registers whose CK is on that tap's net, read from the netlist, never from a register's position).
    upstream(node) -> ("port", name) when the node's net is driven by a block input port, ("next", node') to continue
    through a single-clock-path driver (BUF / INV / clock buffer / ICG CLK input), ("stop", label) for anything else.
    Returns the port name, or "unresolved:<label>" (a loop or depth over max_depth is "unresolved:depth")."""
    node, seen = start, set()
    for _ in range(max_depth):
        if node in seen:
            return "unresolved:loop"
        seen.add(node)
        kind, val = upstream(node)
        if kind == "port":
            return val
        if kind == "stop":
            return f"unresolved:{val}"
        node = val
    return "unresolved:depth"


def _odb_clock_iterm(inst):
    """the clock input ITerm of a register / latch / ICG (LEF USE CLOCK, else a CLOCK_PIN_NAMES name), or None"""
    cand = None
    for it in inst.getITerms():
        mt = it.getMTerm()
        if not it.isInputSignal():
            continue
        if mt.getSigType() == "CLOCK":
            return it
        if mt.getName() in CLOCK_PIN_NAMES and cand is None:
            cand = it
    return cand


def _odb_upstream(iterm):
    """trace_root upstream step on an odb input ITerm"""
    net = iterm.getNet()
    if net is None:
        return ("stop", "no_net")
    for bt in net.getBTerms():
        if bt.getIoType() in ("INPUT", "INOUT"):
            return ("port", bt.getName())
    drv = [it for it in net.getITerms() if it.isOutputSignal()]
    if len(drv) != 1:
        return ("stop", f"drivers{len(drv)}")
    inst = drv[0].getInst(); m = inst.getMaster().getName()
    if m.startswith("ICG"):
        ck = _odb_clock_iterm(inst)
        return ("next", ck) if ck is not None else ("stop", m)
    ins = [it for it in inst.getITerms() if it.isInputSignal()]
    if len(ins) == 1 and not m.startswith(REG_PREFIX):
        return ("next", ins[0])
    return ("stop", m)


def dump_odb(odb_path, out_path):
    import odb
    db = odb.dbDatabase.create()
    odb.read_db(db, odb_path)
    blk = db.getChip().getBlock()
    u = float(blk.getDbUnitsPerMicron())
    cells, macros, roots = [], [], []
    for i in blk.getInsts():
        m = i.getMaster(); n = m.getName(); bb = i.getBBox()
        r = [i.getName(), bb.xMin() / u, bb.yMin() / u, bb.xMax() / u, bb.yMax() / u, n]
        if m.isBlock():
            macros.append(r)
        elif n.startswith(REG_PREFIX):
            cells.append(r)
            ck = _odb_clock_iterm(i)
            roots.append(trace_root(ck, _odb_upstream) if ck is not None else "unresolved:no_clock_pin")
    d = blk.getDieArea()
    # clock_root[i] = the block input port clocking cells[i] (TAP-GRID-R3); readers of the 6-field cells rows are unchanged
    json.dump({"outline": [d.xMin() / u, d.yMin() / u, d.xMax() / u, d.yMax() / u], "cells": cells, "macros": macros,
               "clock_root": roots, "clock_root_basis": "odb CK net traced through BUF/INV/ICG to a block input port"},
              open(out_path, "w"))
    print("TAP_RESOLVE_DUMP", len(cells), "registers", len(macros), "macros", sum(1 for q in roots if q.startswith("unresolved")),
          "unresolved clock roots")


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


def assign(taps, pts, cap=None, max_extra=None):
    """nearest tap (Manhattan) of every point: list of index lists.
    cap: capacity-balanced like the kit (clock_taps.tcl cap pass): a tap over `cap` hands the sinks that cost the least extra
    distance to their next-nearest tap with room (extra <= max_extra um, None = any); repeated until no tap is over or nothing moves."""
    import numpy as np
    A = np.array(taps, dtype=float).reshape(-1, 2); P = np.array(pts, dtype=float).reshape(-1, 2)
    idx = np.empty(len(P), dtype=int)
    for i in range(0, len(P), 4096):
        c = P[i:i + 4096]
        idx[i:i + 4096] = (np.abs(c[:, None, 0] - A[None, :, 0]) + np.abs(c[:, None, 1] - A[None, :, 1])).argmin(axis=1)
    if cap and len(A) > 1:
        load = np.bincount(idx, minlength=len(A))
        for _ in range(20):
            moved = 0
            for k in [int(k) for k in np.argsort(-load) if load[k] > cap]:
                mem = np.nonzero(idx == k)[0]
                D = np.abs(P[mem][:, None, 0] - A[None, :, 0]) + np.abs(P[mem][:, None, 1] - A[None, :, 1])
                own = D[:, k].copy(); D[:, k] = np.inf
                cand = []
                for j in range(len(mem)):
                    for t in np.argsort(D[j])[:6]:
                        e = D[j, t] - own[j]
                        if max_extra is not None and e > max_extra:
                            break
                        if load[t] < cap:
                            cand.append((e, j, int(t))); break
                cand.sort()
                for e, j, t in cand:
                    if load[k] <= cap:
                        break
                    if load[t] < cap:
                        idx[mem[j]] = t; load[t] += 1; load[k] -= 1; moved += 1
            if not moved:
                break
    g = [[] for _ in taps]
    for i, k in enumerate(idx):
        g[k].append(i)
    return g


def tap_stats(taps, pts, radius, cap=None):
    """per tap: (load, sinks beyond radius, p95 distance, max distance, region W+H); cap: capacity-balanced assignment."""
    out = []
    for (x, y), s in zip(taps, assign(taps, pts, cap, radius)):
        ds = sorted(abs(pts[i][0] - x) + abs(pts[i][1] - y) for i in s) or [0.0]
        span = (max(pts[i][0] for i in s) - min(pts[i][0] for i in s)) + (max(pts[i][1] for i in s) - min(pts[i][1] for i in s)) if s else 0.0
        out.append((len(s), sum(1 for v in ds if v > radius), ds[int(0.95 * (len(ds) - 1))], ds[-1], span))
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


def solve(exist, pts, legal, target, radius, core=(), max_add=80, min_new=40, span=None):
    """exist: [(x, y)] kept taps; pts: [(x, y)] registers; -> added [(x, y)]."""
    exist = [tuple(map(float, p)) for p in exist]; core = list(core); added = []
    med = lambda idx, k: st.median(pts[i][k] for i in idx)

    def relax(n):
        nonlocal added
        for _ in range(n):
            g = assign(exist + added, pts, target, radius); new = []
            for k, xy in enumerate(added):
                s = g[len(exist) + k]
                new.append(legalize(med(s, 0), med(s, 1), exist + core + new + added[k + 1:], legal) if s else xy)
            added = new

    def excess(s_):
        if span:
            return sum(max(0, q[0] - target) for q in s_) + sum(max(0.0, q[4] - span) for q in s_)
        return sum(max(0, q[0] - target) for q in s_) + sum(q[1] for q in s_ if q[1] >= FAR_MIN)

    # Split loop (fixed 11-19 after S81-SLICE-C-TAPS: the first form gave up after 6 failed splits in a row and tried one split
    # per tap, so it stalled on iq_C t1 / c1x_C t6 with taps still over the load and the region limit).  Now: the worst tap that is
    # not blocked is split; every candidate cut is tried (region middle and count median, both axes, either half), each first with
    # a relax of all added taps and then without; a tap is blocked only when no candidate lowers the total excess, and every
    # accepted split unblocks all taps (the geometry changed).  Ends when no violating tap is left unblocked, or at max_add.
    def halves(s, x, y, by_mid):
        out = []
        xs = [pts[i][0] for i in s]; ys = [pts[i][1] for i in s]
        first = 0 if (max(xs) - min(xs)) >= (max(ys) - min(ys)) else 1
        for ax in (first, 1 - first):
            v = xs if ax == 0 else ys
            cut = (max(v) + min(v)) / 2.0 if by_mid else st.median(v)
            lo = [i for i in s if pts[i][ax] <= cut]; hi = [i for i in s if pts[i][ax] > cut]
            if not lo or not hi:
                continue
            far_hi = abs((x, y)[ax] - max(v)) >= abs((x, y)[ax] - min(v))
            out += [hi, lo] if far_hi else [lo, hi]
        return out

    blocked = set()
    while len(added) < max_add:
        T = exist + added; g = assign(T, pts, target, radius); s_ = tap_stats(T, pts, radius, target)
        sc = [max(q[0] / target, (q[4] / span) if span else (1.0 + q[1] / FAR_MIN if q[1] >= FAR_MIN else 0.0)) for q in s_]
        order = [i for i in sorted(range(len(T)), key=lambda i: -sc[i]) if sc[i] > 1.0 and T[i] not in blocked]
        if not order:
            break
        k = order[0]; s = g[k]; x, y = T[k]; n, f = s_[k][0], s_[k][1]
        cands = []
        if span and s_[k][4] > span:
            cands += halves(s, x, y, True)
        if (not span) and f >= FAR_MIN:
            cands.append([i for i in s if abs(pts[i][0] - x) + abs(pts[i][1] - y) > radius])
        cands += halves(s, x, y, False)
        if span and s_[k][4] <= span:
            cands += halves(s, x, y, True)
        before = excess(s_); keep = list(added); ok = False
        for far in cands:
            if not far or len(far) == len(s):
                continue
            try:
                site = legalize(med(far, 0), med(far, 1), exist + core + keep, legal)
            except ValueError:
                continue
            for do_relax in (True, False):
                added = keep + [site]
                if do_relax:
                    relax(2)
                s2 = tap_stats(exist + added, pts, radius, target)
                if excess(s2) < before and min(q[0] for q in s2[len(exist):]) >= min_new:
                    ok = True; break
            if ok:
                break
        if ok:
            blocked.clear()
        else:
            added = keep; blocked.add(T[k])
    keep = list(added); before = excess(tap_stats(exist + added, pts, radius, target)) if added else 0
    relax(3)
    if added and excess(tap_stats(exist + added, pts, radius, target)) > before:
        added = keep                                   # the final relax may not undo what the splits reached
    return added


def density_taps(P, tn, regs, span_um=300.0, target=1000, max_add=400, min_new=1, radius=160.0):
    """OPUS-FIX-S81-SLICEC 11-20 (S81 slice C class B: 53 taps for 96k flops): the TAP-DENSITY rule from the PLACED sink
    count -- the same solve as `tap_resolve.py --span-um SPAN --target TARGET` on a register dump of the type.
    -> (append_to key, existing names, added [(x, y)], stats after [(load, beyond, p95, max, W+H)])."""
    import schema, taps
    from placement_obstacles import placement_boxes
    t = P.types[tn]; ck = t.get("clock", {})
    mode = ck.get("tap_mode", "grid")
    if mode not in ("explicit", "grid+explicit"):
        raise ValueError(f"tap density {tn}: clock.tap_mode {mode!r}; explicit or grid+explicit tables only")
    clear = schema.type_tap_clear(t)
    d = regs if isinstance(regs, dict) else json.load(open(regs))
    boxes = list(placement_boxes(t, halo=clear).values()) + [(x0 - clear, y0 - clear, x1 + clear, y1 + clear) for x0, y0, x1, y1 in ck.get("keepouts_um", [])]
    boxes += [(m[1] - clear, m[2] - clear, m[3] + clear, m[4] + clear) for m in d.get("macros", [])]
    legal = make_legal(t["outline_um"], clear, boxes)
    ex = taps.explicit_tap_sites(P, tn) if mode == "explicit" else taps.grid_explicit_sites(P, tn)
    names = [n for n, _, _ in ex]; exist = [(x, y) for _, x, y in ex]
    core = [(x, y) for _, x, y, _ in schema.core_taps(P, tn)]
    pts = [((c[1] + c[3]) / 2, (c[2] + c[4]) / 2) for c in d["cells"]]
    s0 = tap_stats(exist, pts, radius, target)
    need = any(q[4] > span_um or q[0] > target for q in s0)
    added = solve(exist, pts, legal, target, radius, core, max_add, min_new, span_um) if need else []
    return ("taps" if mode == "explicit" else "added_taps"), names, added, tap_stats(exist + added, pts, radius, target)


def apply_density(raw, plan_path, types=None):
    """Plan clock.tap_density {"regs": placed register dump (tap_resolve --dump; path relative to the plan), "span_um": 300,
    "target": 1000}: append the taps the placed sinks need to the type's table (existing taps keep name / xy) and set
    clock.tap_span_um, in `raw`, before the kit is written.  Types without the key are untouched.  -> receipts."""
    import schema
    from pathlib import Path
    out = []
    for tn, t in sorted((raw.get("partition_types") or {}).items()):
        td = (t.get("clock") or {}).get("tap_density")
        if not td or (types and tn not in types):
            continue
        rp = Path(td["regs"])
        if not rp.is_absolute() and plan_path:
            rp = Path(plan_path).resolve().parent / rp
        span = float(td.get("span_um", 300)); target = int(td.get("target", 1000))
        P = schema.Plan(raw, plan_path)
        key, names, added, s1 = density_taps(P, tn, str(rp), span, target, int(td.get("max_add", 400)), int(td.get("min_new", 1)))
        ck = t["clock"]; ck["tap_span_um"] = span
        tab = ck.setdefault(key, [])
        n0 = len(names)
        used = {x.get("name") for x in tab if isinstance(x, dict)} | set(names)
        rows = []
        for i, (x, y) in enumerate(added):
            k = n0 + i
            while f"clk_t{k}" in used:
                k += 1
            used.add(f"clk_t{k}")
            rows.append({"name": f"clk_t{k}", "xy": [round(x, 3), round(y, 3)]})
        tab.extend(rows)
        r = dict(type=tn, regs=str(rp), span_um=span, target=target, taps_before=n0, added=len(rows),
                 max_load=max((q[0] for q in s1), default=0), taps_over_span=sum(1 for q in s1 if q[4] > span))
        print(f"TAP_DENSITY {tn}: {n0} -> {n0 + len(rows)} taps (span {span:g} um, target {target}); max load {r['max_load']}, "
              f"over span {r['taps_over_span']}")
        out.append(r)
    return out


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan"); ap.add_argument("type")
    ap.add_argument("--regs", required=True, help="register dump JSON (--dump)")
    ap.add_argument("--cts-log", help="kit 4_1_cts.log: measured per-tap insertion")
    ap.add_argument("--target", type=int); ap.add_argument("--radius-um", type=float)
    ap.add_argument("--tol-ps", type=float); ap.add_argument("--min-share", type=float, default=0.01)
    ap.add_argument("--span-um", type=float, help="tap sink region W + H limit (300)"); ap.add_argument("--min-new", type=int)
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
    over0 = sum(1 for q in s0 if a.span_um and q[4] > a.span_um)
    min_new = a.min_new if a.min_new is not None else (8 if a.span_um else 40)
    added = solve(exist, pts, legal, target, radius, core, a.max_add, min_new, a.span_um) if (crit["verdict"] == "SPLIT" or over0) else []
    T = exist + added; s1 = tap_stats(T, pts, radius, target)
    allnames = names + [f"clk_t{len(exist) + i}" for i in range(len(added))]
    after = criterion({n: predicted_ps(q[0], q[2]) for n, q in zip(allnames, s1)}, {n: q[0] for n, q in zip(allnames, s1)}, tol, a.min_share)
    for n, (x, y), q in zip(allnames, T, s1):
        m = f" measured {means[n]:.0f} ps" if basis == "MEASURED" and n in means else ""
        print(f"  {n:8s} ({x:8.2f},{y:8.2f}) sinks {q[0]:6d} beyond-radius {q[1]:5d} p95 {q[2]:5.0f} um W+H {q[4]:5.0f}{m}{'  ADDED' if n not in names else ''}")
    print(f"TAP_RESOLVE {a.type}: added {len(added)}, max load {max(q[0] for q in s1)}, sinks beyond radius {sum(q[1] for q in s1)}, predicted spread after {after['spread_ps']} ps" + (f"; sink region W+H > {a.span_um:g} um: {over0} taps before, {sum(1 for q in s1 if q[4] > a.span_um)} after (max {max(q[4] for q in s1):.0f})" if a.span_um else ""))
    json.dump({"schema": "opentallas.tap_resolve.v1", "type": a.type, "plan": a.plan, "regs": a.regs, "registers": len(pts), "criterion": crit,
               "predicted_after": after, "target_sinks": target, "radius_um": radius, "append_to": "clock.taps" if mode == "explicit" else "clock.added_taps",
               "added_taps": [{"name": f"clk_t{len(exist) + i}", "xy": [x, y]} for i, (x, y) in enumerate(added)],
               "load": {n: q[0] for n, q in zip(allnames, s1)}, "span_um": {n: round(q[4], 1) for n, q in zip(allnames, s1)},
               "span_limit_um": a.span_um, "taps_over_span": [n for n, q in zip(allnames, s1) if a.span_um and q[4] > a.span_um]}, open(a.out, "w"), indent=1)
    return 0


if __name__ == "__main__":
    if "--dump" in sys.argv:
        dump_odb(os.environ["ODB"], os.environ["OUT"])
    else:
        sys.exit(main())
