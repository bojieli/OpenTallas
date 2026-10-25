"""Sink-anchored clock taps (COORD 10-23 R4, GEOM-REVIEW6 17:09, KV-P6).

A partition whose clock sinks are FIRM-planned (face registers at their pins, ft stations on their planned routes, the
per-tap reset synchronisers) may ADD clock taps at those sinks to its ceil(w/pitch) x ceil(h/pitch) grid (KV-P6
motivation: a coarse grid left 6/12 (400 um) and 11/20 (280 um) io_cor_v1 taps without a sink (dead spine drops, unloaded
per-tap reset synchronisers) while the loaded taps held 2.7k sinks / 349-ps trees.

    clock.tap_mode      "grid+sinks" / "sinks" (default "grid": schema.tap_grid's pitch grid).  CP1 r8 RULING (COORD
                        10-23 21:26): these taps are ADDED to the R4 grid (schema.tap_grid), never replace it -- as a
                        replacement the frame's interior logic (4.5-5.7k sinks) piled on one tap (spread 133 ps)
    clock.tap_radius_um max Manhattan distance tap -> planned sink (default 250: the 280-um grid's 205-222 ps trees)
    clock.tap_max_sinks max planned sinks per sink tap (clustering default 1500); clock_taps.tcl caps the real
                        netlist per tap (grid or added) at OT_TAP_MAX_SINKS = this value, else 3000

Method: the planned sinks (planned_sinks) are clustered by capacity- and radius-bounded Manhattan k-medians: k grows
from ceil(N / cap) until every cluster fits the radius and the cap; a tap sits at its cluster's coordinate-wise median
(the L1 centre), clamped TAP_MARGIN_UM inside the outline; empty clusters are dropped, so every tap carries planned
sinks.  Deterministic (farthest-point seeding from the sink nearest the outline centre).  Tap 0 = 'clk' is the tap
nearest the plan's clock.tap_um (the die spine's partition root), the rest 'clk_t<i>' in (y, x) order.

clock.tap_mode "density" (OWNER decision 5, 10-24, industry multi-source CTS; opt-in, density_taps): NO grid.  Taps are
placed by sink density over the full register inventory (clock.sink_bins_file from a placed netlist via
`taps.py bins`, and/or clock.sink_sites_um, else the planned face / ft sinks): <= tap_target_sinks (0.8 x
tap_max_sinks, default 1500) per tap within tap_radius_um (200), none on a hard core (keep-clear), refined on the kit's
own nearest-tap + cap split (assign = clock_taps.tcl).  gen_phys exports OT_TAP_REASSIGN_UM = radius and the GRT-RC tap
hook (tap_balance_grt.tcl, clock.tap_balance_rc grt_report | grt | placement).
"""
import math

TAP_MARGIN_UM = 17.28          # keep the interior tap pins off the face pin bands
FACE_INSET_UM = 2.0            # a face register sits just inside its pin
SEP_UM = 8.64                  # two taps closer than one lattice step merge (one spine drop)

_CACHE = {}


def _zroute(a, b, fin, fout):
    """face_flops.tcl ff_zroute: the slot's planned route as a polyline."""
    (ax, ay), (bx, by) = a, b
    if abs(ax - bx) < 1 or abs(ay - by) < 1:
        return [a, b]
    if (fin in "EW") != (fout in "EW"):
        return [a, (bx, ay), b] if fin in "EW" else [a, (ax, by), b]
    if fin in "EW":
        xm = (ax + bx) / 2
        return [a, (xm, ay), (xm, by), b]
    ym = (ay + by) / 2
    return [a, (ax, ym), (bx, ym), b]


def _point_at(pts, t):
    for (px, py), (qx, qy) in zip(pts, pts[1:]):
        d = abs(px - qx) + abs(py - qy)
        if t <= d:
            f = 0.0 if d == 0 else t / d
            return (px + f * (qx - px), py + f * (qy - py))
        t -= d
    return pts[-1]


def _inset(x, y, face, w, h):
    return {"E": (x - FACE_INSET_UM, y), "W": (x + FACE_INSET_UM, y), "N": (x, y - FACE_INSET_UM),
            "S": (x, y + FACE_INSET_UM)}.get(face, (x, y))


def planned_sinks(P, tn):
    """[(x, y, kind)] type-frame sites of the type's FIRM-planned clock sinks: one face register per bus pin (in and
    out ports register at the face, R2), ft slot station 0 at each in pin and stations j = 1..k-1 at L*j/k along the
    slot route (or at regs_um), as face_flops.tcl places them.  ft out pins carry no sink (the neighbour's station 0)."""
    import gen_phys
    t = P.types[tn]
    w, h = t["outline_um"]
    slots = {s["name"]: s for s in t.get("ft_slots", [])}
    pins = gen_phys.type_pins(P, tn)
    at = {(p[0], p[1]): (p[3], p[4], p[5]) for p in pins}
    out = []
    for name, bit, _ln, x, y, face in pins:
        base, sfx = (name[:-2], name[-2:]) if name[-2:] in ("_i", "_o") else (name, "")
        if base in slots and sfx:
            if sfx == "_o":
                continue
            s = slots[base]
            out.append(_inset(x, y, face, w, h) + ("ft_s0",))
            k = int(s.get("stations", 1))
            o = at.get((base + "_o", bit))
            if k < 2 or o is None:
                continue
            regs = s.get("regs_um", [])
            pts = _zroute((x, y), (o[0], o[1]), s["in_face"], s["out_face"])
            L = sum(abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(pts, pts[1:]))
            for j in range(1, k):
                xy = tuple(regs[j]) if len(regs) >= k else _point_at(pts, L * j / k)
                out.append((xy[0], xy[1], f"ft_s{j}"))
        else:
            out.append(_inset(x, y, face, w, h) + ("face",))
    return out


def _median(v):
    s = sorted(v)
    n = len(s)
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def _kmedians(pts, k, iters=25):
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    seed = min(pts, key=lambda p: (abs(p[0] - cx) + abs(p[1] - cy), p))
    cen = [seed]
    dmin = [abs(p[0] - seed[0]) + abs(p[1] - seed[1]) for p in pts]
    while len(cen) < k:
        i = max(range(len(pts)), key=lambda j: (dmin[j], -j))
        c = pts[i]
        cen.append(c)
        dmin = [min(d, abs(p[0] - c[0]) + abs(p[1] - c[1])) for d, p in zip(dmin, pts)]
    asg = None
    for _ in range(iters):
        new = [min(range(len(cen)), key=lambda c: (abs(p[0] - cen[c][0]) + abs(p[1] - cen[c][1]), c)) for p in pts]
        if new == asg:
            break
        asg = new
        groups = [[] for _ in cen]
        for p, a in zip(pts, asg):
            groups[a].append(p)
        cen = [(_median([p[0] for p in g]), _median([p[1] for p in g])) if g else c for g, c in zip(groups, cen)]
    groups = [[] for _ in cen]
    for p, a in zip(pts, asg):
        groups[a].append(p)
    return cen, groups


def _root():
    from pathlib import Path
    return Path(__file__).resolve().parents[2]


def sink_sites(P, tn):
    """[(x, y, weight)] type-frame clock sinks for clock.tap_mode "density": the FIRM planned sinks (planned_sinks,
    weight 1) plus the plan's internal sink inventory -- clock.sink_sites_um ([x, y] or [x, y, n] rows) -- or, with
    clock.sink_bins_file (the full register inventory of a placed netlist, which already holds the face / ft
    registers, so planned_sinks are then left out) plus any sink_sites_um.  The bins file is repo-relative JSON
    {"bin_um": b, "bins": [[x, y, n], ...]}, written by `taps.py bins <odb dump.json>`: the registers of a placed
    netlist binned to their bin centres."""
    ck = P.types[tn].get("clock", {})
    rows = list(ck.get("sink_sites_um", []))
    if ck.get("sink_bins_file"):
        # a placed netlist's inventory already holds the face / ft registers: the planned ones are not added again
        import json
        rows += json.loads((_root() / ck["sink_bins_file"]).read_text())["bins"]
        out = []
    else:
        out = [(x, y, 1.0) for x, y, _ in planned_sinks(P, tn)]
    out += [(float(r[0]), float(r[1]), float(r[2]) if len(r) > 2 else 1.0) for r in rows]
    return [p for p in out if p[2] > 0]


def _wmedian(pts, i):
    """weighted median of coordinate i (lower median on ties: deterministic)."""
    s = sorted(pts, key=lambda p: (p[i], p[1 - i]))
    tot, acc = sum(p[2] for p in s), 0.0
    for p in s:
        acc += p[2]
        if acc >= tot / 2:
            return p[i]
    return s[-1][i]


def _bisect(pts, target, radius, blocked=lambda x, y: False, min_sinks=1):
    """capacity- and radius-bounded weighted median bisection (a balanced kd split along the longer extent): every leaf
    holds <= target sinks within `radius` (Manhattan) of its weighted L1 centre.  Unlike k-medians with coincident
    seeds, a dense bank can never silently overflow a tap: it is split until it fits (a single site heavier than the
    target stays one leaf).  A leaf whose centre falls in a keep-clear (`blocked`: a hard core) is split further, so
    a group straddling a core becomes one tap on each side instead of one tap pushed to the core edge."""
    pending, leaves = [pts], []
    while pending:
        g = pending.pop()
        x, y = _wmedian(g, 0), _wmedian(g, 1)
        n = sum(p[2] for p in g)
        r = max(abs(p[0] - x) + abs(p[1] - y) for p in g)
        if len(g) == 1 or (n <= target and r <= radius and not blocked(x, y)):
            leaves.append((x, y, n, r, g))
            continue
        ax = max((0, 1), key=lambda i: (max(p[i] for p in g) - min(p[i] for p in g), -i))
        g = sorted(g, key=lambda p: (p[ax], p[1 - ax]))
        acc, k = 0.0, 1
        for k, p in enumerate(g[:-1], 1):
            acc += p[2]
            if acc >= n / 2:
                break
        pending += [g[k:], g[:k]]
    return _absorb(_merge(leaves, target, radius, blocked), target, min_sinks, radius)


def _absorb(leaves, target, min_sinks, radius):
    """Merge light clusters only while every sink stays within the tap radius.

    A remote control bank needs its own spine drop even when it has few sinks;
    attaching it to a data band creates a long clock arm and delays that band.
    """
    leaves = sorted(leaves, key=lambda a: (-a[2], round(a[1], 3), round(a[0], 3)))
    keep = [q for q in leaves if q[2] >= min_sinks]
    if not keep:
        return leaves
    for x, y, n, _, g in (q for q in leaves if q[2] < min_sinks):
        room = [k for k, q in enumerate(keep) if q[2] + n <= target
                and all(abs(p[0]-q[0])+abs(p[1]-q[1]) <= radius for p in g)]
        if not room:
            keep.append((x, y, n, max(abs(p[0]-x)+abs(p[1]-y) for p in g), g))
            continue
        k = min(room, key=lambda k: (abs(keep[k][0] - x) + abs(keep[k][1] - y), k))
        a = keep[k]
        keep[k] = (a[0], a[1], a[2] + n, max(a[3], max(abs(p[0] - a[0]) + abs(p[1] - a[1]) for p in g)), a[4] + g)
    return keep


def _merge(leaves, target, radius, blocked=lambda x, y: False):
    """bisection cuts along the median, so a sparse channel or an L-shaped region ends up in many small leaves (dead-ish
    taps of a few hundred sinks next to each other).  Greedily merge the pair of leaves whose union still fits the
    target and radius with the smallest merged radius, until no pair fits.  Deterministic."""
    leaves = list(leaves)
    while True:
        best = None
        for i, a in enumerate(leaves):
            for j in range(i + 1, len(leaves)):
                b = leaves[j]
                if a[2] + b[2] > target or abs(a[0] - b[0]) + abs(a[1] - b[1]) > 2 * radius:
                    continue
                g = a[4] + b[4]
                x, y = _wmedian(g, 0), _wmedian(g, 1)
                r = max(abs(p[0] - x) + abs(p[1] - y) for p in g)
                if r <= radius and not blocked(x, y) and (best is None or (r, i, j) < best[:3]):
                    best = (r, i, j, (x, y, a[2] + b[2], r, g))
        if best is None:
            return leaves
        _, i, j, m = best
        leaves = [q for k, q in enumerate(leaves) if k not in (i, j)] + [m]


def density_taps(P, tn):
    """OWNER decision 5 (10-24, industry multi-source CTS): partition clock taps placed by SINK DENSITY.

    The sinks (sink_sites: face / ft registers + the internal inventory) are split by weighted median bisection into
    leaves of <= clock.tap_target_sinks (default 0.8 x tap_max_sinks, so the kit's nearest-tap split of the real netlist
    stays under the hard cap clock_taps.tcl enforces) within clock.tap_radius_um (default 200) of their centre (a leaf
    centred on a hard core splits on; small neighbours merge; a stray leaf of < clock.tap_min_sinks, default target /
    20, joins its nearest tap).  Each
    leaf's tap sits at its weighted L1 centre, legalised by schema.tap_clear(strict): >= TAP_CLEAR_UM off every hard
    core (keep-clear: no tap buffer on a macro), inside the outline, off the taps already placed and off the early
    core tap pins.  No grid: an empty region gets no tap, a dense region gets as many as its load needs.  Tap 0 'clk'
    = the tap nearest clock.tap_um, the others 'clk_t<i>' in (y, x) order.  The leaves then seed a capacitated
    k-medians refinement on the kit's own split rule (assign: nearest tap + cap), so the planned load of every tap is
    what clock_taps.tcl will give it.  Deterministic.
    Returns [(port, x, y, planned_sinks (kit split at the hard cap), max sink distance um)]."""
    key = ("density", id(P), tn)
    if key in _CACHE:
        return _CACHE[key]
    import schema
    t = P.types[tn]
    ck = t.get("clock", {})
    cap = int(ck.get("tap_max_sinks", 1500))
    target = int(ck.get("tap_target_sinks", max(1, int(0.8 * cap))))
    radius = float(ck.get("tap_radius_um", 200.0))
    if cap <= 0 or target <= 0 or radius <= 0 or target > cap:
        raise ValueError(f"type {tn}: density taps need 0 < tap_target_sinks <= tap_max_sinks and tap_radius_um > 0")
    pts = sink_sites(P, tn)
    if not pts:
        raise ValueError(f"type {tn}: clock.tap_mode 'density' but no sinks (no pins / ft slots / sink inventory)")
    w, h = t["outline_um"]
    taken = [(x, y) for _, x, y, _ in schema.core_taps(P, tn)]
    boxes = [(c["origin_um"][0], c["origin_um"][1], c["origin_um"][0] + c["outline_um"][0],
              c["origin_um"][1] + c["outline_um"][1]) for c in t.get("hard_cores", []) or []]
    blocked = lambda x, y: any(x0 < x < x1 and y0 < y < y1 for x0, y0, x1, y1 in boxes)
    min_sinks = int(ck.get("tap_min_sinks", max(1, target // 20)))
    leaves = sorted(_bisect(pts, target, radius, blocked, min_sinks), key=lambda a: (round(a[1], 3), round(a[0], 3)))

    def place(cands):
        tk, xy = list(taken), []
        for x, y in cands:
            x = min(max(x, TAP_MARGIN_UM), w - TAP_MARGIN_UM)
            y = min(max(y, TAP_MARGIN_UM), h - TAP_MARGIN_UM)
            x, y = schema.tap_clear(t, x, y, tk, strict=True)
            tk.append((x, y))
            xy.append((round(x, 4), round(y, 4)))
        return xy
    # refine (capacitated k-medians seeded by the leaves): the kit splits the netlist by NEAREST tap + cap
    # (clock_taps.tcl, mirrored by assign()), so re-centre every tap on the sinks that split gives it, re-legalise,
    # Drop only empty taps. A light, isolated control cluster must keep its tap:
    # its radius cannot be traded for reaching a preferred minimum sink count.
    xy = place([(q[0], q[1]) for q in leaves])
    for _ in range(int(ck.get("tap_refine_iters", 6))):
        _, _, asg = assign([(None, x, y) for x, y in xy], pts, target, radius)
        groups = [[] for _ in xy]
        for p, j in zip(pts, asg):
            groups[j].append(p)
        keep = [j for j, g in enumerate(groups) if g]
        nxt = place([(_wmedian(groups[j], 0), _wmedian(groups[j], 1)) if groups[j] else xy[j] for j in keep])
        if nxt == xy:
            break
        xy = nxt
    load, far, _ = assign([(None, x, y) for x, y in xy], pts, cap, radius)
    out = sorted(((x, y, int(round(n)), round(r, 1)) for (x, y), n, r in zip(xy, load, far) if n > 0),
                 key=lambda q: (q[1], q[0]))
    root = ck.get("tap_um", [w / 2, h / 2])
    i0 = min(range(len(out)), key=lambda i: (abs(out[i][0] - root[0]) + abs(out[i][1] - root[1]), i))
    out = [out[i0]] + [p for i, p in enumerate(out) if i != i0]
    res = [("clk" if i == 0 else f"clk_t{i}", x, y, n, r) for i, (x, y, n, r) in enumerate(out)]
    _CACHE[key] = res
    return res


def assign(taps, sinks, cap, max_extra_um):
    """Python mirror of clock_taps.tcl (the kit's sink -> tap split, for G0 / review): every sink (x, y, w) to its
    NEAREST tap (Manhattan, ties to the lower tap index), then capacity-constrained re-assignment: while a tap holds
    > cap, its sinks that cost the least extra distance move to the best other tap with room, at most max_extra_um
    further.  Returns (per-tap load, per-tap max distance, [tap index per sink]).  Deterministic."""
    xy = [(t[1], t[2]) for t in taps]
    d = lambda s, j: abs(s[0] - xy[j][0]) + abs(s[1] - xy[j][1])
    asg = [min(range(len(xy)), key=lambda j: (d(s, j), j)) for s in sinks]
    load = [0.0] * len(xy)
    for s, j in zip(sinks, asg):
        load[j] += s[2]
    stuck = set()
    for _ in range(8 * len(xy)):
        over = next((j for j in range(len(xy)) if j not in stuck and load[j] > cap), None)
        if over is None:
            break
        cand = []
        for i, s in enumerate(sinks):
            if asg[i] != over:
                continue
            best = min(((d(s, j) - d(s, over), j) for j in range(len(xy)) if j != over and load[j] < cap),
                       default=None)
            if best and best[0] <= max_extra_um:
                cand.append((best[0], i, best[1]))
        if not cand:
            stuck.add(over)
            continue
        cand.sort()
        tgt = cand[0][2]
        for _, i, j in cand:
            if load[over] <= cap or load[tgt] >= cap:
                break
            if j != tgt:
                continue
            asg[i] = tgt
            load[over] -= sinks[i][2]
            load[tgt] += sinks[i][2]
    far = [0.0] * len(xy)
    for s, j in zip(sinks, asg):
        far[j] = max(far[j], d(s, j))
    return load, far, asg


def bins_from_dump(dump, bin_um=10.8, origin=(0.0, 0.0)):
    """{"bin_um", "bins": [[x, y, n]]} of the clocked registers (DFF* / ICG* / SDF* / DHL* / DLL* masters) of an odb
    geometry dump ({"cells": [[name, x0, y0, x1, y1, master], ...]}), binned at bin_um, sites at the bin centres."""
    import collections
    c = collections.Counter()
    for _, x0, y0, x1, y1, m in dump["cells"]:
        if not any(k in m for k in ("DFF", "ICG", "SDF", "DHL", "DLL")):
            continue
        cx, cy = (x0 + x1) / 2 - origin[0], (y0 + y1) / 2 - origin[1]
        c[(int(cx // bin_um), int(cy // bin_um))] += 1
    return dict(bin_um=bin_um, n=sum(c.values()),
                bins=[[round((i + 0.5) * bin_um, 3), round((j + 0.5) * bin_um, 3), n] for (i, j), n in sorted(c.items())])


def sink_taps(P, tn):
    """[(port, x, y, n_sinks, radius_um)] sink-anchored taps of type tn (cached per plan object and type)."""
    if P.types[tn].get("clock", {}).get("tap_mode") == "density":
        return density_taps(P, tn)
    key = (id(P), tn)
    if key in _CACHE:
        return _CACHE[key]
    t = P.types[tn]
    ck = t.get("clock", {})
    w, h = t["outline_um"]
    R = float(ck.get("tap_radius_um", 250.0))
    cap = int(ck.get("tap_max_sinks", 1500))
    pts = [(x, y) for x, y, _ in planned_sinks(P, tn)]
    if not pts:
        raise ValueError(f"type {tn}: clock.tap_mode 'sinks' but no planned sinks (no pins / ft slots)")
    k = max(1, math.ceil(len(pts) / cap))
    while True:
        cen, groups = _kmedians(pts, k)
        taps = []
        for (x, y), g in zip(cen, groups):
            if not g:
                continue
            x = min(max(x, TAP_MARGIN_UM), w - TAP_MARGIN_UM)
            y = min(max(y, TAP_MARGIN_UM), h - TAP_MARGIN_UM)
            r = max(abs(p[0] - x) + abs(p[1] - y) for p in g)
            taps.append([x, y, len(g), r])
        if all(tp[3] <= R and tp[2] <= cap for tp in taps) or k >= len(pts) or k >= 256:
            break
        k += 1
    # one spine drop per lattice step: merge near-coincident taps
    merged = []
    for tp in sorted(taps, key=lambda q: (round(q[1], 3), round(q[0], 3))):
        m = next((q for q in merged if abs(q[0] - tp[0]) + abs(q[1] - tp[1]) < SEP_UM), None)
        if m:
            m[2] += tp[2]
            m[3] = max(m[3], tp[3])
        else:
            merged.append(tp)
    root = ck.get("tap_um", [w / 2, h / 2])
    i0 = min(range(len(merged)), key=lambda i: (abs(merged[i][0] - root[0]) + abs(merged[i][1] - root[1]), i))
    order = [merged[i0]] + [q for i, q in enumerate(merged) if i != i0]
    out = [("clk" if i == 0 else f"clk_t{i}", round(q[0], 4), round(q[1], 4), q[2], round(q[3], 1))
           for i, q in enumerate(order)]
    _CACHE[key] = out
    return out


def report(P, tn):
    """kit / G0 summary of the sink-anchored taps."""
    taps = sink_taps(P, tn)
    ck = P.types[tn].get("clock", {})
    dens = ck.get("tap_mode") == "density"
    return dict(mode=ck.get("tap_mode", "sinks"), radius_um=float(ck.get("tap_radius_um", 200.0 if dens else 250.0)),
                max_sinks=int(ck.get("tap_max_sinks", 1500)), n=len(taps), empty=sum(1 for t in taps if t[3] == 0),
                taps=[dict(name=n, xy=[x, y], planned_sinks=s, radius_um=r) for n, x, y, s, r in taps])


if __name__ == "__main__":
    import argparse
    import json
    ap = argparse.ArgumentParser(description="clock.sink_bins_file from a placed partition's odb geometry dump")
    ap.add_argument("cmd", choices=["bins"])
    ap.add_argument("dump", help="odb dump JSON (cells: [name, x0, y0, x1, y1, master]; outline: [x0, y0, x1, y1])")
    ap.add_argument("--bin-um", type=float, default=10.8)
    ap.add_argument("--src", default="", help="provenance note stored in the file")
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()
    d = json.load(open(a.dump))
    b = bins_from_dump(d, a.bin_um, tuple(d.get("outline", [0, 0])[:2]))
    b["src"] = a.src
    open(a.out, "w").write(json.dumps(b, separators=(",", ":")) + "\n")
    print(f"{a.out}: {b['n']} registers in {len(b['bins'])} bins of {a.bin_um} um")
