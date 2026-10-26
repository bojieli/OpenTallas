#!/usr/bin/env python3
"""INFRA-SITE SUFFICIENCY gate (COORD/owner 2026-10-26; lanes/INFRA-FIRST.md NEXT 1).  Opt-in, read-only, any die.

Called as `die_infra.py sites PLAN --out D [--mesh MESH] [--tracks preroute.json] [--pg pg.json] [--m89]
[--bays bays.json]`; writes D/infra_sites.json (+ D/infra_sites_summary.json, D/core_bays.tsv) and exits 1 on FAIL.

Owner/COORD rules this gate measures (no other rule is invented here):
  * die signals are pushed-down partition logic: every feedthrough station / repeater sits in a PARTITION REPEATER
    BAY (std-cell area of a soft partition, or a declared in-core bay of a hard core); partitions abut; no die-level
    std cells for signals.  Bay-to-bay gap along a corridor <= reach (405 um, plan die.reach_um / ruling 9.3).
  * INFRA ISLANDS = top-owned holes with an M9->M1 via stack, for the die clock (H-tree nodes/repeaters, mesh
    drivers) and the regional reset register / repeaters ONLY; one island per partition at the type's clock tap
    (QC: the 147-um A0 channel cross).  The die H-tree lattice snaps to the island lattice.

Checks (each FAILs closed; a check with no data is NOT RUN and the verdict cannot be PASS):
  (a) corridors: every ft slot crossing (lane in-port -> declared regs_um -> out-port) and every type
      internal_station route (from_um -> regs_um -> to_um).  Each leg between registers is routed Manhattan (HV, VH,
      or a Z through a soft column/row, detour <= --detour-um); sites = partition rect - hard cores - island
      + declared in-core bays.  max gap <= reach.  Hard cores whose straight crossing exceeds reach are listed with a
      proposed in-core bay (die + core-local coordinates) or the leftover-M8/M9 alternative.
  (b) cut use: cut lines every budgets.cut_step_um across each partition; bits of corridor legs crossing the cut /
      tracks of the crossing-direction M4-M7 layers (layers <= --core-obs-top blocked over hard cores; island
      blocks all) [+ leftover M8/M9 from --tracks when --m89] <= budgets.cut_ratio_max (0.6).
  (c) porosity: per-gcell via-stack limit = --stack-util x min over M2-M9 of the free tracks in one gcell (M8/M9
      free = 1 - tracks_taken from --tracks, else the PG grid's stripes + spacing; M2-M7 inside an island lose
      --lower-pg-frac to the island's own PG).  Island demand: 2 stacks per clock/reset cell x parallel vias for EM;
      M8/M9 signal drops (only for cores that need the M8/M9 alternative): 2 x bits over the corridor window gcells.
  (d) fill: partition bay fill = (declared est. std-cell fill + ft station flops + repeaters) / soft area <= 0.6;
      in-core bay sized to <= 0.6; island fill <= 0.6; island power density <= --island-w-mm2 and EM
      (driver I_avg = C V f per output stack vs --via-imax-ma per via).
H-tree snap (--mesh): every H-tree node -> nearest island centre; max node displacement per level, sibling-leg
equality after the snap (mismatch + serpentine wire to restore it), clock leg gap between islands vs --clock-reach
(mesh meta rep_um), reset hops (reset_tree wavefront) gap between islands vs --reset-reach.
Model constants (stated, not measured): BUFx24 1.62 x 0.27 um, station flop 1.404 x 0.27 um (plan bit_site_cell_um),
repeater BUFx4 0.378 x 0.27 um, clock C_int 2 fF/cell, wire 0.2 fF/um, V = 0.70 (TT), f = 1 / die.period_ps.
"""
import json
import math
import re
from collections import defaultdict
from pathlib import Path

ROW = 0.27
A_BUF24 = 1.620 * ROW
A_REP = 0.378 * ROW
A_FLOP = 1.404 * ROW
C_INT_F = 2e-15
C_WIRE_F_UM = 0.2e-15
G = 10.8                                    # GRT gcell (die_infra.track_use)
LANE_OF_DIE = [(r"head", "HEAD-CORE-LAT"), (r"hbm", "HBM-CORE-LAT"), (r"s81|ds", "S81-CORE-LAT"),
               (r"qwen|qc", "QC-SU-LAT")]


def lane_for(die_name):
    for pat, lane in LANE_OF_DIE:
        if re.search(pat, die_name, re.I):
            return lane
    return "CORES"


# ------------------------------------------------------------------------------------------------------ intervals
def union(iv):
    out = []
    for a, b in sorted(iv):
        if b <= a:
            continue
        if out and a <= out[-1][1] + 1e-9:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [tuple(x) for x in out]


def subtract(iv, cut):
    out = []
    for a, b in iv:
        segs = [(a, b)]
        for c, d in cut:
            nxt = []
            for x, y in segs:
                if d <= x or c >= y:
                    nxt.append((x, y))
                    continue
                if c > x:
                    nxt.append((x, c))
                if d < y:
                    nxt.append((d, y))
            segs = nxt
        out += segs
    return union(out)


def seg_cover(a, b, rects):
    """parameter intervals [t0, t1] (um from a) of the axis-aligned segment a->b inside any rect (closed)."""
    (x0, y0), (x1, y1) = a, b
    L = abs(x1 - x0) + abs(y1 - y0)
    if L < 1e-9:
        return []
    out = []
    horiz = abs(y1 - y0) < 1e-9
    for r in rects:
        rx0, ry0, rx1, ry1 = r[:4]
        if horiz:
            if not (ry0 - 1e-9 <= y0 <= ry1 + 1e-9):
                continue
            lo, hi = sorted((x0, x1))
            c, d = max(lo, rx0), min(hi, rx1)
            if d <= c:
                continue
            t = sorted(((c - x0) if x1 >= x0 else (x0 - c), (d - x0) if x1 >= x0 else (x0 - d)))
        else:
            if not (rx0 - 1e-9 <= x0 <= rx1 + 1e-9):
                continue
            lo, hi = sorted((y0, y1))
            c, d = max(lo, ry0), min(hi, ry1)
            if d <= c:
                continue
            t = sorted(((c - y0) if y1 >= y0 else (y0 - c), (d - y0) if y1 >= y0 else (y0 - d)))
        out.append((max(0.0, t[0]), min(L, t[1])))
    return union(out)


def seg_len(a, b):
    return abs(b[0] - a[0]) + abs(b[1] - a[1])


def point_at(a, b, t):
    L = seg_len(a, b)
    if L < 1e-9:
        return tuple(a)
    f = t / L
    return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)


def poly_gap(pts, site_iv):
    """longest run along polyline pts with no site; site_iv(a, b) -> site intervals of segment a->b.  The first and
    last points are registers (sites); a run continues across a corner.  -> (gap um, midpoint, start, end)."""
    best, where = 0.0, None
    run, start = 0.0, None
    for a, b in zip(pts, pts[1:]):
        L = seg_len(a, b)
        if L < 1e-9:
            continue
        cur = 0.0
        for c, d in site_iv(a, b):
            if d - c <= 1e-9:
                continue
            if c > cur + 1e-9:
                if run == 0.0:
                    start = point_at(a, b, cur)
                run += c - cur
                if run > best:
                    best, where = run, (start, point_at(a, b, c))
            run = 0.0
            cur = max(cur, d)
        if L > cur + 1e-9:
            if run == 0.0:
                start = point_at(a, b, cur)
            run += L - cur
            if run > best:
                best, where = run, (start, tuple(b))
    if where is None:
        return 0.0, None, None, None
    s, e = where
    return round(best, 3), ((s[0] + e[0]) / 2, (s[1] + e[1]) / 2), s, e


# --------------------------------------------------------------------------------------------------- geometry
def rect_pts(P, part, r):
    (x0, y0), (x1, y1) = P.to_die(part, (r[0], r[1])), P.to_die(part, (r[2], r[3]))
    return (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


def type_cores(t):
    """[(x0, y0, x1, y1, inst, module)] hard cores in the type frame."""
    out = []
    for h in t.get("hard_cores", []):
        (ox, oy), (w, hh) = h["origin_um"], h["outline_um"]
        out.append((ox, oy, ox + w, oy + hh, h["inst"], h["module"]))
    return out


def core_bays(t, bays):
    """declared in-core bays in the type frame: hard_cores[i].bays_um (core-local rects) + --bays {module: [rects]}."""
    out = []
    for h in t.get("hard_cores", []):
        ox, oy = h["origin_um"]
        w, hh = h["outline_um"]
        rs = list(h.get("bays_um", [])) + list((bays or {}).get(h["module"], []))
        o = h.get("orient", "R0")
        for x0, y0, x1, y1 in rs:
            # core-local -> type frame through the core orient
            X0, X1 = (w - x1, w - x0) if o in ("MY", "R180") else (x0, x1)
            Y0, Y1 = (hh - y1, hh - y0) if o in ("MX", "R180") else (y0, y1)
            out.append((ox + X0, oy + Y0, ox + X1, oy + Y1, h["inst"], h["module"]))
    return out


def free_square(t, tap):
    """largest square centred on tap clear of every hard core and inside the outline (type frame) -> side um."""
    w, h = t["outline_um"]
    x, y = tap
    s = min(x, y, w - x, h - y)
    for x0, y0, x1, y1, *_ in type_cores(t):
        dx = max(x0 - x, x - x1, 0.0)
        dy = max(y0 - y, y - y1, 0.0)
        s = min(s, max(dx, dy))
    return 2 * s


def note_fill(t):
    m = re.search(r"std-cell fill ([0-9.]+)", t.get("note", "") or "")
    return float(m.group(1)) if m else None


# ------------------------------------------------------------------------------------------------- corridors
def leg_routes(a, b, blockers, box, detour):
    """candidate Manhattan routes a -> b: HV, VH and Z routes through soft columns/rows within the partition box."""
    (ax, ay), (bx, by) = a, b
    R = [[a, (bx, ay), b], [a, (ax, by), b]]
    xs, ys = {box[0] + 1, box[2] - 1}, {box[1] + 1, box[3] - 1}
    for x0, y0, x1, y1, *_ in blockers:
        xs |= {x0 - 1, x1 + 1}
        ys |= {y0 - 1, y1 + 1}
    base = seg_len(a, b)
    for c in xs:
        if box[0] <= c <= box[2]:
            r = [a, (c, ay), (c, by), b]
            if sum(seg_len(p, q) for p, q in zip(r, r[1:])) - base <= detour + 1e-6:
                R.append(r)
    for c in ys:
        if box[1] <= c <= box[3]:
            r = [a, (ax, c), (bx, c), b]
            if sum(seg_len(p, q) for p, q in zip(r, r[1:])) - base <= detour + 1e-6:
                R.append(r)
    return R


def make_site_iv(box, blockers, bays):
    def iv(a, b):
        s = seg_cover(a, b, [box])
        s = subtract(s, seg_cover(a, b, blockers))
        return union(s + seg_cover(a, b, bays))
    return iv


def route_leg(a, b, box, blockers, bays, reach, detour):
    iv = make_site_iv(box, blockers, bays)
    best = None
    straight = None
    for k, r in enumerate(leg_routes(a, b, blockers, box, detour)):
        g, mid, s, e = poly_gap(r, iv)
        ln = sum(seg_len(p, q) for p, q in zip(r, r[1:]))
        key = (g > reach + 1e-6, ln, g)
        if k < 2 and (straight is None or g < straight[0]):
            straight = (g, mid, r)
        if best is None or key < best[0]:
            best = (key, g, mid, r, ln)
    return dict(gap=best[1], mid=best[2], route=best[3], len=best[4], straight_gap=straight[0],
                straight_mid=straight[1], straight_route=straight[2], manhattan=seg_len(a, b))


def corridors(P):
    """[(part, name, kind, bits, [die points incl. registers], layers)] for every ft slot crossing + internal station."""
    out, seen = [], set()
    for lid in P.lanes:
        try:
            xs = P.lane_crossings(lid)
        except KeyError:
            continue
        for part, slot, pin, pout in xs:
            if not slot or part not in P.parts or (part, slot) in seen:
                continue
            s = P.slot(part, slot)
            if s is None:
                continue
            seen.add((part, slot))
            try:
                a, b = P.port_point(pin), P.port_point(pout)
            except (KeyError, TypeError):
                continue
            regs = [P.to_die(part, tuple(r)) for r in s.get("regs_um", [])]
            out.append((part, slot, "ft_slot", int(s["width"]), [a] + regs + [b], s.get("layers", [])))
    for part, p in P.parts.items():
        t = P.types[p["type"]]
        for k, st in enumerate(t.get("internal_stations", [])):
            pts = [st["from_um"]] + st.get("regs_um", []) + [st["to_um"]]
            out.append((part, f"istn{k}:{st.get('conn', '')}", "internal_station", int(st.get("bits", 1)),
                        [P.to_die(part, tuple(q)) for q in pts], []))
    return out


# --------------------------------------------------------------------------------------------------- tracks
def die_free_frac(P, layer, pg_grid, tracks):
    """free track fraction of a die layer: 1 - tracks_taken (preroute.json) else 1 - PG stripes incl. spacing."""
    if tracks and layer in tracks:
        return max(0.0, 1.0 - float(tracks[layer]["all"]))
    p = P.layers[layer]["pitch_um"]
    blk = 0.0
    for g in pg_grid:
        if g["layer"] != layer:
            continue
        n = len(g.get("nets", ["VDD", "VSS"]) or ["VDD"])
        blk += n / g["pitch_um"] * math.ceil((g["width_um"] + 2 * 0.04) / p - 1e-9) * p
    return max(0.0, 1.0 - blk)


def stack_limit(P, pg_grid, tracks, lower_pg_frac, util):
    """per-gcell M9->M1 via-stack limit (escape-limited by the coarsest free layer) + per-layer free tracks."""
    free = {}
    for L, d in P.layers.items():
        cap = G / d["pitch_um"]
        frac = die_free_frac(P, L, pg_grid, tracks) if L in ("M8", "M9") else 1.0 - lower_pg_frac
        free[L] = round(cap * frac, 2)
    worst = min(free, key=free.get)
    return int(util * free[worst]), worst, free


# ------------------------------------------------------------------------------------------------------- main
def run(P, mesh_dir=None, tracks_file=None, pg_file=None, m89=False, bays=None, reach=None, detour=405.0,
        core_obs_top="M5", stack_util=0.5, lower_pg_frac=0.25, fill_max=0.6, island_w_mm2=2.0, via_imax_ma=0.05,
        clock_reach=None, reset_reach=1000.0, with_reset=True, island_min_um=21.6):
    reach = float(reach or P.reach)
    period = float(P.die.get("period_ps", 833.0))
    f_hz = 1e12 / period
    V = 0.70
    pg_grid = json.loads(Path(pg_file).read_text())["grid"] if pg_file else P.die.get("pg", {}).get("grid", [])
    tracks = json.loads(Path(tracks_file).read_text()).get("tracks_taken") if tracks_file else None
    cut_max = float(P.budgets.get("cut_ratio_max", 0.6))
    step = float(P.budgets.get("cut_step_um", 250.0))
    rep = dict(plan=str(P.path), die=P.name, reach_um=reach, detour_um=detour, model=dict(
        core_obs_top=core_obs_top, stack_util=stack_util, lower_pg_frac=lower_pg_frac, fill_max=fill_max,
        island_w_mm2=island_w_mm2, via_imax_ma=via_imax_ma, m89=m89, f_hz=f_hz, V=V, gcell_um=G,
        a_buf24_um2=A_BUF24, a_rep_um2=A_REP, a_flop_um2=A_FLOP))
    checks = {}

    # ---------------- islands (type frame, sized after demand)
    taps = {}
    for tn, t in P.types.items():
        tp = (t.get("clock") or {}).get("tap_um") or (t.get("reset") or {}).get("tap_um")
        if tp is None:
            w, h = t["outline_um"]
            tp = (w / 2, h / 2)
        taps[tn] = tuple(tp)
    centre = {p: P.to_die(p, taps[P.parts[p]["type"]]) for p in P.parts}

    # ---------------- clock demand: drivers by containment, H-tree nodes/reps snapped to the nearest island
    demand = defaultdict(lambda: defaultdict(float))
    snap = None
    part_list = list(P.parts)
    rects = {p: P.rect(p) for p in part_list}
    bucket = defaultdict(list)
    BK = 500.0
    for p, r in rects.items():
        for i in range(int(r[0] // BK), int(r[2] // BK) + 1):
            bucket[i].append(p)

    def part_at(x, y):
        for p in bucket.get(int(x // BK), []):
            r = rects[p]
            if r[0] - 1e-6 <= x <= r[2] + 1e-6 and r[1] - 1e-6 <= y <= r[3] + 1e-6:
                return p
        return None
    cpts = sorted((c[0], c[1], p) for p, c in centre.items())
    cx = [c[0] for c in cpts]
    import bisect

    def nearest_island(x, y):
        best, bp = None, None
        i = bisect.bisect_left(cx, x)
        span = 0
        while True:
            span += 1
            lo, hi = max(0, i - 8 * span), min(len(cpts), i + 8 * span)
            for X, Y, p in cpts[lo:hi]:
                d = abs(X - x) + abs(Y - y)
                if best is None or d < best:
                    best, bp = d, p
            if best is not None and (lo == 0 or abs(cpts[lo][0] - x) > best) and \
                    (hi == len(cpts) or abs(cpts[hi - 1][0] - x) > best):
                return bp, best
            if lo == 0 and hi == len(cpts):
                return bp, best
    mesh_meta = None
    island_rects_die = {}     # filled after the island sizing (also without --mesh: no H-tree snap then)
    if mesh_dir:
        md = Path(mesh_dir)
        M = json.loads((md / "mesh.json").read_text())
        mesh_meta = M["meta"]
        cells = json.loads((md / "place.json").read_text())
        cr = md / "clock_report.json"
        cap_pf = None
        if cr.exists():
            cap_pf = json.loads(cr.read_text())["corners"].get("TT", {}).get("mesh_cap_pF")
        nbuf = mesh_meta.get("bufx24_drivers") or sum(len(d["cells"]) for d in M["drivers"].values())
        c_drv = (cap_pf * 1e-12 / nbuf if cap_pf else 0.06e-12) + C_INT_F
        clock_reach = float(clock_reach or mesh_meta.get("rep_um", 450.0))
        drv_move = []
        for d in M["drivers"].values():
            x, y = d["site"]
            p = part_at(x, y) or nearest_island(x, y)[0]
            k = len(d["cells"])
            demand[p]["drivers"] += k
            demand[p]["power_w"] += k * c_drv * V * V * f_hz
            demand[p]["i_drv_ma"] = c_drv * V * f_hz * 1e3
            c = centre[p]
            drv_move.append((abs(c[0] - x) + abs(c[1] - y), d["i"], d["j"], p))
        drv_move.sort(reverse=True)
        # H-tree nodes: leg endpoints b (level >= 1) + the root
        legs = M["htree"]
        node_pt = {}
        for e in legs:
            node_pt[(e["level"], e["tag"])] = tuple(e["b"])
        snapped = {}
        disp_by_level = defaultdict(float)
        worst_node = None
        for (lv, tag), (x, y) in node_pt.items():
            p, d = nearest_island(x, y)
            snapped[(lv, tag)] = (p, centre[p], d)
            disp_by_level[lv] = max(disp_by_level[lv], d)
            if worst_node is None or d > worst_node[0]:
                worst_node = (d, lv, tag, (x, y), p, centre[p])
        n_isl = len(P.parts)
        lv_counts = defaultdict(int)
        for lv, _ in node_pt:
            lv_counts[lv] += 1
        island_level = max([lv for lv, n in lv_counts.items() if n <= n_isl] or [0])
        # sibling-leg equality after the snap (legs with the same parent point a)
        fam = defaultdict(list)
        parent_of = {}
        for e in legs:
            fam[(e["level"], round(e["a"][0], 2), round(e["a"][1], 2))].append(e)
        by_b = {(e["level"], round(e["b"][0], 2), round(e["b"][1], 2)): e for e in legs}
        mism, extra, mism_lv = 0.0, 0.0, defaultdict(float)
        collapsed = 0
        for (lv, ax, ay), es in fam.items():
            if lv > island_level:
                continue
            pe = by_b.get((lv - 1, ax, ay))
            pa = snapped[(lv - 1, pe["tag"])][1] if pe else (ax, ay)
            ls = []
            for e in es:
                cb = snapped[(lv, e["tag"])][1]
                ls.append(abs(cb[0] - pa[0]) + abs(cb[1] - pa[1]))
            if min(ls) < 1e-6:
                collapsed += 1
            m = max(ls) - min(ls)
            mism = max(mism, m)
            mism_lv[lv] = max(mism_lv[lv], m)
            extra += sum(max(ls) - v for v in ls)
            for e in es:
                parent_of[(lv, e["tag"])] = pa
        # clock cells landing per island: nodes (one per tree node <= island_level, deeper levels are the in-island
        # distribution) + leg repeaters (ceil(leg / clock_reach) - 1 after the snap, sited at islands on the leg)
        for (lv, tag), (p, c, d) in snapped.items():
            if lv <= island_level:
                demand[p]["nodes"] += 1
                demand[p]["power_w"] += (C_INT_F + 2e-15) * V * V * f_hz
        rep_cells = sum(1 for c in cells.values() if c.get("kind") == "rep")
        snap = dict(levels=dict(sorted(lv_counts.items())), islands=n_isl, island_level=island_level,
                    max_node_disp_um=round(worst_node[0], 2) if worst_node else None,
                    max_node_disp_to_island_level_um=round(max([v for lv, v in disp_by_level.items()
                                                                if lv <= island_level] or [0]), 2),
                    disp_by_level_um={lv: round(v, 2) for lv, v in sorted(disp_by_level.items())},
                    worst_node=dict(disp_um=round(worst_node[0], 2), level=worst_node[1], tag=worst_node[2],
                                    node_um=worst_node[3], island_part=worst_node[4],
                                    island_um=[round(v, 3) for v in worst_node[5]]) if worst_node else None,
                    sibling_mismatch_max_um=round(mism, 2), sibling_mismatch_by_level_um={
                        lv: round(v, 2) for lv, v in sorted(mism_lv.items())},
                    equal_legs_hold=mism < 1.0, serpentine_extra_mm=round(extra / 1e3, 3),
                    collapsed_families=collapsed, builder_rep_cells=rep_cells, clock_reach_um=clock_reach,
                    driver_sites=len(M["drivers"]), driver_move_to_island_max_um=round(drv_move[0][0], 2),
                    driver_move_worst=[dict(um=round(m, 1), i=i, j=j, part=p) for m, i, j, p in drv_move[:5]],
                    note="levels <= island_level keep a node per island (nodes per level <= islands); deeper levels "
                         "and the mesh drivers collapse into the island of their partition (in-island fan-out)")
        snap["_legs"] = [(lv, tag, parent_of.get((lv, tag)), snapped[(lv, tag)][1]) for (lv, tag) in snapped
                         if lv <= island_level and (lv, tag) in parent_of]
        checks["htree_snap"] = "INFO"
    else:
        checks["htree_snap"] = "NOT RUN"

    # ---------------- reset demand per island (regional reset register + repeaters ONLY)
    reset_hops = []
    if with_reset:
        try:
            import die_infra as DI
            W, wires = DI.reset_wires(P)
            T = W["types"]
            for p, r in W["parts"].items():
                tn = r["type"]
                tt = T.get(tn, {})
                n = int(P.reset.get("sync_stages", 2)) + int(tt.get("entry_stages", 1) or 0) + len(tt.get("outs", []))
                demand[p]["reset_cells"] += n
                demand[p]["power_w"] += n * 0.2 * (C_INT_F * 2) * V * V * f_hz      # 20 % activity flops/bufs
            for net, kind, a, b in wires:
                reset_hops.append((net, kind, a, b))
            checks["reset_demand"] = "INFO"
        except Exception as ex:                       # noqa: BLE001 -- recorded, verdict cannot PASS on it
            checks["reset_demand"] = f"NOT RUN ({type(ex).__name__}: {ex})"

    # ---------------- island sizing per type (a type is hardened once: max demand over its instances)
    lim, lim_layer, free_tracks = stack_limit(P, pg_grid, tracks, lower_pg_frac, stack_util)
    by_type = defaultdict(list)
    for p in P.parts:
        by_type[P.parts[p]["type"]].append(p)
    islands = {}
    isl_fail = []
    for tn, ps in by_type.items():
        t = P.types[tn]
        dm = {k: max(demand[p][k] for p in ps) for k in ("drivers", "nodes", "reset_cells", "power_w", "i_drv_ma")}
        cells_n = dm["drivers"] + dm["nodes"] + dm["reset_cells"]
        area = (dm["drivers"] + dm["nodes"]) * A_BUF24 + dm["reset_cells"] * A_FLOP
        par = max(1, math.ceil(dm["i_drv_ma"] / via_imax_ma)) if dm["i_drv_ma"] else 1
        stacks = 2 * ((dm["drivers"] + dm["nodes"]) * par + dm["reset_cells"])
        # island side = max of: cell fill <= fill_max, via stacks <= limit per gcell, power <= island_w_mm2
        need = dict(min=island_min_um, fill=math.sqrt(area / fill_max) if cells_n else 0.0,
                    porosity=G * math.sqrt(stacks / lim) if stacks and lim else (0.0 if not stacks else 1e9),
                    power=math.sqrt(dm["power_w"] / island_w_mm2) * 1e3 if dm["power_w"] else 0.0)
        side_need = math.ceil(max(need.values()) / P.grid - 1e-9) * P.grid
        side_free = free_square(t, taps[tn])
        side = side_need if side_free >= side_need else math.floor(side_free / P.grid + 1e-9) * P.grid
        tx, ty = taps[tn]
        rect_t = [round(tx - side / 2, 3), round(ty - side / 2, 3), round(tx + side / 2, 3), round(ty + side / 2, 3)]
        fill = area / (side * side) if side > 0 else float("inf")
        isl_gc = max(1.0, (side / G) ** 2)
        per_gc = stacks / isl_gc if stacks else 0.0
        dens = dm["power_w"] / (side * side * 1e-6) if side > 0 else float("inf")
        ok = side_free >= side_need and fill <= fill_max + 1e-9 and per_gc <= lim and dens <= island_w_mm2 + 1e-9
        row = dict(type=tn, instances=len(ps), tap_um=list(taps[tn]), rect_um=rect_t, side_um=round(side, 3),
                   side_need_um=round(side_need, 3), side_need_by={k: round(v, 2) for k, v in need.items()},
                   side_free_um=round(side_free, 3), drivers_bufx24=dm["drivers"],
                   htree_nodes=dm["nodes"], reset_cells=dm["reset_cells"], cell_area_um2=round(area, 2),
                   fill=round(fill, 4), power_mw=round(dm["power_w"] * 1e3, 3), w_per_mm2=round(dens, 4),
                   i_avg_per_driver_ma=round(dm["i_drv_ma"], 4), parallel_vias=par, stacks=int(stacks),
                   stacks_per_gcell=round(per_gc, 2), stack_limit_per_gcell=lim,
                   stack_margin=round(lim / per_gc, 2) if per_gc else None, verdict="PASS" if ok else "FAIL")
        islands[tn] = row
        if not ok:
            isl_fail.append(tn)
    for p in P.parts:
        island_rects_die[p] = rect_pts(P, p, islands[P.parts[p]["type"]]["rect_um"])

    # ---------------- (a) corridors
    blk_cache, bay_cache = {}, {}

    def blockers(p):
        if p not in blk_cache:
            t = P.types[P.parts[p]["type"]]
            blk_cache[p] = [rect_pts(P, p, c[:4]) + c[4:] for c in type_cores(t)] + \
                [tuple(island_rects_die[p]) + ("island", "island")]
            bay_cache[p] = [rect_pts(P, p, c[:4]) + c[4:] for c in core_bays(t, bays)]
        return blk_cache[p], bay_cache[p]
    rows = []
    crossings = defaultdict(lambda: dict(max_run=0.0, bits=0, corridors=0, forced=0))
    cut_bits = defaultdict(list)                        # part -> [(segment a, b, bits)]
    for part, name, kind, bits, pts, layers in corridors(P):
        box = rects[part]
        blk, bay = blockers(part)
        worst = None
        legs_out = []
        for a, b in zip(pts, pts[1:]):
            r = route_leg(a, b, box, blk, bay, reach, detour)
            legs_out.append(r)
            for q0, q1 in zip(r["route"], r["route"][1:]):
                cut_bits[part].append((q0, q1, bits))
            # per-core along-length on the straight route (the in-core bay question) and on the chosen route
            for rt, tagk in ((r["straight_route"], "straight"), (r["route"], "chosen")):
                for c in blk:
                    if c[4] == "island":
                        continue
                    run = 0.0
                    for q0, q1 in zip(rt, rt[1:]):
                        cov = subtract(seg_cover(q0, q1, [c]), seg_cover(q0, q1, bay))
                        run = max(run, max([d - e for e, d in cov] or [0.0]))
                    if tagk == "straight" and run > reach + 1e-6:
                        k = (P.parts[part]["type"], c[4], c[5])
                        crossings[k]["max_run"] = max(crossings[k]["max_run"], run)
                        crossings[k]["bits"] = max(crossings[k]["bits"], bits)
                        crossings[k]["corridors"] += 1
                        crossings[k]["forced"] += int(r["gap"] > reach + 1e-6)
            if worst is None or r["gap"] > worst["gap"]:
                worst = r
        rows.append(dict(part=part, name=name, kind=kind, bits=bits, gap_um=worst["gap"],
                         at_um=[round(v, 2) for v in worst["mid"]] if worst["mid"] else None,
                         straight_gap_um=max(r["straight_gap"] for r in legs_out),
                         detour_um=round(sum(r["len"] - r["manhattan"] for r in legs_out), 2),
                         legs=len(legs_out), verdict="PASS" if worst["gap"] <= reach + 1e-6 else "FAIL",
                         route=[[round(v, 2) for v in q] for r in legs_out for q in r["route"]]))
    rows.sort(key=lambda r: -r["gap_um"])
    nfail = sum(r["verdict"] == "FAIL" for r in rows)
    checks["a_corridor_gap"] = ("PASS" if not nfail else "FAIL") if rows else "NOT RUN"

    # ---------------- per-core table: cores with an extent > reach along any axis + corridor evidence
    core_rows = []
    lane = lane_for(P.name)
    seen = set()
    for tn, t in P.types.items():
        for h in t.get("hard_cores", []):
            w, hh = h["outline_um"]
            key = (tn, h["inst"])
            if max(w, hh) <= reach + 1e-6 or key in seen:
                continue
            seen.add(key)
            ev = crossings.get((tn, h["inst"], h["module"]))
            bays_loc = []
            for axis, ext, across in (("y", hh, w), ("x", w, hh)):
                if ext <= reach + 1e-6:
                    continue
                n = math.ceil(ext / reach) - 1
                bits = ev["bits"] if ev else 0
                band = max(P.grid / 2, math.ceil(bits * (A_REP + A_FLOP) / fill_max / across / ROW) * ROW)
                for k in range(1, n + 1):
                    c = ext * k / (n + 1)
                    loc = [0.0, round(c - band / 2, 3), round(w, 3), round(c + band / 2, 3)] if axis == "y" else \
                        [round(c - band / 2, 3), 0.0, round(c + band / 2, 3), round(hh, 3)]
                    bays_loc.append(dict(axis=axis, core_local_um=loc, band_um=round(band, 3),
                                         max_gap_after_um=round(ext / (n + 1), 2)))
            inst_die = []
            for p in by_type[tn]:
                o = h.get("orient", "R0")
                for b in bays_loc:
                    x0, y0, x1, y1 = b["core_local_um"]
                    X0, X1 = (w - x1, w - x0) if o in ("MY", "R180") else (x0, x1)
                    Y0, Y1 = (hh - y1, hh - y0) if o in ("MX", "R180") else (y0, y1)
                    ox, oy = h["origin_um"]
                    inst_die.append(dict(part=p, axis=b["axis"], die_um=[round(v, 3) for v in rect_pts(
                        P, p, (ox + X0, oy + Y0, ox + X1, oy + Y1))]))
            need = bool(ev and ev["forced"])
            m89_drops = None
            if ev:
                win_gc = max(1.0, (ev["bits"] * 0.064 * 2) / G)          # corridor window ~ bits x M7 pitch / 2 layers
                m89_drops = round(2 * ev["bits"] / win_gc, 2)
            core_rows.append(dict(lane=lane, type=tn, inst=h["inst"], module=h["module"], outline_um=[w, hh],
                                  origin_um=h["origin_um"], orient=h.get("orient", "R0"), instances=len(by_type[tn]),
                                  corridors_straight_over_reach=ev["corridors"] if ev else 0,
                                  corridors_forced=ev["forced"] if ev else 0,
                                  max_straight_run_um=round(ev["max_run"], 2) if ev else 0.0,
                                  bits_max=ev["bits"] if ev else 0,
                                  status="NEEDS_IN_CORE_BAY_OR_M89" if need else
                                  ("DETOUR_OK" if ev else "GEOMETRIC_ONLY(no corridor crosses)"),
                                  proposed_bays=bays_loc, proposed_bays_die=inst_die[:64],
                                  m89_drops_per_gcell=m89_drops, m89_drop_limit_per_gcell=lim))
    core_rows.sort(key=lambda r: (r["status"] != "NEEDS_IN_CORE_BAY_OR_M89", -r["max_straight_run_um"]))

    # ---------------- (b) cut use
    order = sorted(P.layers, key=lambda n: int(n[1:]))
    sig = [L for L in order if 4 <= int(L[1:]) <= 7]
    obs_top = int(core_obs_top[1:])
    cut_rows = []
    for part, segs in cut_bits.items():
        x0, y0, x1, y1 = rects[part]
        blk, _bay = blockers(part)
        for axis in ("h", "v"):            # h: horizontal cut line y=c, crossed by vertical legs
            lo, hi = (y0, y1) if axis == "h" else (x0, x1)
            c = lo + step
            while c < hi - 1e-6:
                bits = 0
                for a, b, n in segs:
                    if axis == "h" and abs(a[0] - b[0]) < 1e-9 and min(a[1], b[1]) < c < max(a[1], b[1]):
                        bits += n
                    if axis == "v" and abs(a[1] - b[1]) < 1e-9 and min(a[0], b[0]) < c < max(a[0], b[0]):
                        bits += n
                if bits:
                    span = (x1 - x0) if axis == "h" else (y1 - y0)
                    tr = 0.0
                    for L in sig + (["M8", "M9"] if m89 else []):
                        d = P.layers[L]
                        if (axis == "h") != (d["dir"] == "V"):
                            continue
                        blocked = 0.0
                        for r in blk:
                            on = (r[1] <= c <= r[3]) if axis == "h" else (r[0] <= c <= r[2])
                            if on and (r[4] == "island" or int(L[1:]) <= obs_top):
                                blocked += (r[2] - r[0]) if axis == "h" else (r[3] - r[1])
                        frac = die_free_frac(P, L, pg_grid, tracks) if L in ("M8", "M9") else 1.0
                        tr += max(0.0, span - blocked) / d["pitch_um"] * frac
                    cut_rows.append(dict(part=part, axis=axis, at_um=round(c, 2), bits=bits, tracks=int(tr),
                                         use=round(bits / tr, 4) if tr else float("inf"),
                                         ft_track_frac=P.types[P.parts[part]["type"]].get("ft_track_frac")))
                c += step
    cut_rows.sort(key=lambda r: -r["use"])
    checks["b_cut_use"] = ("PASS" if not cut_rows or cut_rows[0]["use"] <= cut_max else "FAIL") if rows else "NOT RUN"

    # ---------------- (d) partition bay fill
    fill_rows = []
    rep_bits = defaultdict(float)
    for r in rows:
        stations = max(0, r["legs"] - 1)
        n_rep = 0
        pts = r["route"]
        ln = sum(seg_len(a, b) for a, b in zip(pts, pts[1:]))
        n_rep = max(0, math.ceil(ln / max(1, r["legs"]) / reach) - 1) * r["legs"]
        rep_bits[r["part"]] += r["bits"] * (stations * A_FLOP + n_rep * A_REP)
    no_note = 0
    for p in P.parts:
        t = P.types[P.parts[p]["type"]]
        w, h = t["outline_um"]
        core_a = sum((c[2] - c[0]) * (c[3] - c[1]) for c in type_cores(t))
        isl = islands[P.parts[p]["type"]]["side_um"] ** 2
        soft = w * h - core_a - isl
        base = note_fill(t)
        if base is None:
            no_note += 1
        f = (base or 0.0) + (rep_bits[p] / soft if soft > 0 else float("inf"))
        fill_rows.append(dict(part=p, type=P.parts[p]["type"], soft_um2=round(soft, 1), base_fill=base,
                              ft_cell_um2=round(rep_bits[p], 1), fill=round(f, 4)))
    fill_rows.sort(key=lambda r: -r["fill"])
    checks["d_bay_fill"] = "PASS" if fill_rows and fill_rows[0]["fill"] <= fill_max else "FAIL"
    checks["d_island"] = "PASS" if not isl_fail else "FAIL"
    checks["c_porosity"] = "PASS" if all(r["stacks_per_gcell"] <= lim for r in islands.values()) else "FAIL"
    if not mesh_dir:
        checks["d_island"] = "NOT RUN (no --mesh: island clock demand unknown)"
        checks["c_porosity"] = "NOT RUN (no --mesh)"

    # ---------------- clock legs / reset hops between islands (M8/M9 repeaters only in islands)
    isl_list = [(tuple(r) + ("isl", p)) for p, r in island_rects_die.items()]

    def isl_iv(a, b):
        return seg_cover(a, b, isl_list)
    if snap:
        worst = (0.0, None, None)
        for lv, tag, pa, cb in snap.pop("_legs"):
            rt = [pa, (cb[0], pa[1]), cb]
            g, mid, *_ = poly_gap(rt, isl_iv)
            if g > worst[0]:
                worst = (g, lv, mid)
        nn = []
        for X, Y, p in cpts:
            d = min((abs(X2 - X) + abs(Y2 - Y)) for X2, Y2, q in cpts if q != p)
            nn.append((d, p))
        nn.sort(reverse=True)
        snap["island_nn_hop_max_um"] = round(nn[0][0], 2)
        snap["island_nn_hop_worst_part"] = nn[0][1]
        snap["island_nn_hop_median_um"] = round(nn[len(nn) // 2][0], 2)
        snap["clock_leg_island_gap_max_um"] = round(worst[0], 2)
        snap["clock_leg_island_gap_where"] = dict(level=worst[1], at_um=[round(v, 1) for v in worst[2]]) \
            if worst[2] else None
        checks["clock_leg_reach"] = "PASS" if worst[0] <= clock_reach + 1e-6 else "FAIL"
    if reset_hops:
        worst = (0.0, None, None)
        for net, kind, a, b in reset_hops:
            g, mid, *_ = poly_gap([a, (b[0], a[1]), b], isl_iv)
            if g > worst[0]:
                worst = (g, net, mid)
        rep["reset_hops"] = dict(hops=len(reset_hops), island_gap_max_um=round(worst[0], 2), worst_net=worst[1],
                                 at_um=[round(v, 1) for v in worst[2]] if worst[2] else None,
                                 reset_reach_um=reset_reach)
        checks["reset_hop_reach"] = "PASS" if worst[0] <= reset_reach + 1e-6 else "FAIL"

    verdict = "PASS" if all(v == "PASS" or v == "INFO" for v in checks.values()) else \
        ("FAIL" if any(v == "FAIL" for v in checks.values()) else "NOT RUN")
    need = [c for c in core_rows if c["status"] == "NEEDS_IN_CORE_BAY_OR_M89"]
    summ = dict(
        verdict=verdict, checks=checks, corridors=len(rows), corridors_fail=nfail,
        worst_gap=rows[0] if rows else None, worst_gaps=[{k: v for k, v in r.items() if k != "route"}
                                                         for r in rows[:15]],
        cores_over_reach=len(core_rows), cores_needing_in_core_bay=len(need),
        core_types_needing_bay=sorted({(c["module"], tuple(c["outline_um"])) for c in need}),
        worst_cut=cut_rows[0] if cut_rows else None, cuts_over=sum(r["use"] > cut_max for r in cut_rows),
        cut_max=cut_max, worst_bay_fill=fill_rows[0] if fill_rows else None,
        bay_fill_parts_without_fill_note=no_note,
        stack_limit_per_gcell=lim, stack_limit_layer=lim_layer, free_tracks_per_gcell=free_tracks,
        island_worst={k: max(islands.values(), key=lambda r: r[k] or 0)[k] for k in (
            "fill", "w_per_mm2", "stacks_per_gcell", "power_mw", "side_need_um")},
        island_min_free_side_um=min(r["side_free_um"] for r in islands.values()),
        island_types_fail=isl_fail, htree_snap=snap, reset_hops=rep.get("reset_hops"))
    rep.update(summary=summ, islands=islands, cores=core_rows, corridors=rows, cuts=cut_rows[:200],
               bay_fill=fill_rows,
               island_instances={p: dict(type=P.parts[p]["type"], die_um=[round(v, 3) for v in island_rects_die[p]],
                                         centre_um=[round(v, 3) for v in centre[p]],
                                         drivers=demand[p]["drivers"], nodes=demand[p]["nodes"],
                                         reset_cells=demand[p]["reset_cells"]) for p in P.parts})
    return rep


def write(rep, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "infra_sites.json").write_text(json.dumps(rep, indent=1, default=str) + "\n")
    (out / "infra_sites_summary.json").write_text(json.dumps(rep["summary"], indent=1, default=str) + "\n")
    with open(out / "core_bays.tsv", "w") as f:
        f.write("lane\ttype\tinst\tmodule\toutline_um\tstatus\tmax_straight_run_um\tbits\tbay_axis\t"
                "core_local_um\tmax_gap_after_um\n")
        for c in rep["cores"]:
            for b in c["proposed_bays"] or [{}]:
                f.write(f"{c['lane']}\t{c['type']}\t{c['inst']}\t{c['module']}\t{c['outline_um']}\t{c['status']}\t"
                        f"{c['max_straight_run_um']}\t{c['bits_max']}\t{b.get('axis', '')}\t"
                        f"{b.get('core_local_um', '')}\t{b.get('max_gap_after_um', '')}\n")
    with open(out / "islands.tsv", "w") as f:
        f.write("type\tinstances\ttap_um\tisland_rect_type_um\tside_need\tside_free\tdrivers\tnodes\treset\tfill\t"
                "mW\tW_mm2\tstacks_gcell\tlimit\tverdict\n")
        for r in rep["islands"].values():
            f.write(f"{r['type']}\t{r['instances']}\t{r['tap_um']}\t{r['rect_um']}\t{r['side_need_um']}\t"
                    f"{r['side_free_um']}\t{r['drivers_bufx24']}\t{r['htree_nodes']}\t{r['reset_cells']}\t"
                    f"{r['fill']}\t{r['power_mw']}\t{r['w_per_mm2']}\t{r['stacks_per_gcell']}\t"
                    f"{r['stack_limit_per_gcell']}\t{r['verdict']}\n")


def render(P, rep, out, window=None, dpi=200):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    win = window or [0, 0, P.W, P.H]
    ww, wh = win[2] - win[0], win[3] - win[1]
    sc = max(ww, wh) / 16.0
    fig, ax = plt.subplots(figsize=(ww / sc, wh / sc), dpi=dpi)

    def inwin(r):
        return r[2] >= win[0] and r[0] <= win[2] and r[3] >= win[1] and r[1] <= win[3]
    for p in P.parts:
        r = P.rect(p)
        if not inwin(r):
            continue
        ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fill=False, lw=0.3, ec="0.5"))
        t = P.types[P.parts[p]["type"]]
        for c in type_cores(t):
            q = rect_pts(P, p, c[:4])
            ax.add_patch(Rectangle((q[0], q[1]), q[2] - q[0], q[3] - q[1], fc="0.85", ec="0.6", lw=0.2))
        if window:
            ax.text((r[0] + r[2]) / 2, r[3] - 20, p, fontsize=4, color="0.35", ha="center", va="top", clip_on=True)
    for p, d in rep["island_instances"].items():
        r = d["die_um"]
        if inwin(r):
            s = max(r[2] - r[0], (60 if not window else 0))
            cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
            ok = rep["islands"][d["type"]]["verdict"] == "PASS"
            ax.add_patch(Rectangle((cx - s / 2, cy - s / 2), s, s, fc="tab:red" if not ok else "tab:blue",
                                   ec="none", alpha=0.8))
    for c in rep["cores"]:
        for b in c["proposed_bays_die"]:
            r = b["die_um"]
            if inwin(r):
                ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], max(r[3] - r[1], 4), fc="tab:green", ec="none",
                                       alpha=0.9))
    reach = rep["reach_um"]
    for r in rep["corridors"]:
        pts = r["route"]
        g = r["gap_um"]
        col = "tab:red" if g > reach else ("tab:orange" if g > 0.75 * reach else "tab:cyan")
        xs, ys = [q[0] for q in pts], [q[1] for q in pts]
        if max(xs) < win[0] or min(xs) > win[2] or max(ys) < win[1] or min(ys) > win[3]:
            continue
        ax.plot(xs, ys, color=col, lw=0.4 if g <= reach else 0.9, alpha=0.8)
    for r in rep["corridors"][:8]:
        if r["at_um"] and win[0] <= r["at_um"][0] <= win[2] and win[1] <= r["at_um"][1] <= win[3]:
            ax.plot(*r["at_um"], "x", color="k", ms=4, mew=0.8)
            ax.text(r["at_um"][0], r["at_um"][1], f" {r['gap_um']:.0f}", fontsize=5)
    s = rep["summary"]
    ax.set_xlim(win[0], win[2])
    ax.set_ylim(win[1], win[3])
    ax.set_aspect("equal")
    hs = s.get("htree_snap") or {}
    ax.set_title(f"{P.name} INFRA-SITE {s['verdict']}: worst corridor gap {s['worst_gap']['gap_um'] if s['worst_gap'] else '-'}"
                 f" um (reach {reach:.0f}), cores needing in-core bay {s['cores_needing_in_core_bay']}, "
                 f"worst cut {s['worst_cut']['use'] if s['worst_cut'] else '-'}, bay fill "
                 f"{s['worst_bay_fill']['fill'] if s['worst_bay_fill'] else '-'}; islands blue/red(FAIL), bays green,"
                 f" corridors cyan/orange/red; H-tree snap max {hs.get('max_node_disp_to_island_level_um')} um"
                 + (f"  window {win}" if window else ""), fontsize=6)
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out
