#!/usr/bin/env python3
"""INFRA-FIRST-HEAD-3 (R3, D-INFRA-FIRST-HEAD): s81_head island/channel-quantised global tree + ONE continuous die mesh
(12.8e/e1) + edge-pin stubs (COORD ruling INFRA-FIRST-HEAD-2 ASK2) + plan-level mesh gates.  Plan geometry only.

Structure (die frame):
  root (plan clock.spine.root_um) -> y-trunk on the spine column x = 8760.96 (hd_spn soft, station-band soft partitions)
  -> per driver row an x-tree on a CHANNEL row: the hd_tile horizontal channel between the eA rows (tile-frame
  y 354.24, eA bottom ends 326.31 / eA top starts 380.16, MY-invariant, crosses no hard core on the whole half) and the
  station tap row (type-frame y 613.44) -> mesh drivers at the hd_tile channel cross (354.24, 354.24) = the 12.2a
  partition channel-cross island, and at the station-row x M9-column crossings -> continuous mesh: M8 straps on every
  island row (eA 168.48 / channel 354.24 / eA 540.00 / eB 876.96 per tile row) + station rows + serdes strip rows, M9
  straps on every island column (tile x 177.12 / 354.24 / 531.36) -> stubs to every core / partition clock entry.
The tree is qc_clk_mesh3.grid_tree (delay-balanced, equal stages, straight legs) on that grid.  Every tree node and
leg repeater is then classified against the plan (hard cores + 1.08 clearance, PHY zones, reserve frames, partitions).
All numbers UNCHECKED until NUMBER-CHECK."""
import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "die_plan"))
import qc_clk_mesh3 as Q  # noqa: E402

CLR = 1.08
CH_Y = 354.24          # hd_tile horizontal channel row (tile frame)
ROWS_T = (168.48, CH_Y, 540.0, 876.96)   # M8 mesh rows per tile row (tile frame)
COLS_T = (177.12, 354.24, 531.36)        # M9 mesh columns per tile column (tile frame)
ST_ROW = 613.44        # station-type tap row (type frame, = half height)
SD_ROW = 77.76         # hd_serdes digital-strip tap row (type frame)
TRUNK_X = 8760.96
STATIONS = ("hd_st_turn", "hd_st_str", "hd_st_n3", "hd_st_n4", "hd_st_m", "hd_st_k5", "hd_mesh", "hd_lep0N", "hd_ctl",
            "hd_host")


def r3(v):
    return round(float(v), 3)


def tf(o, ox, oy, w, h, x, y):
    return {"R0": (ox + x, oy + y), "MY": (ox + w - x, oy + y), "MX": (ox + x, oy + h - y),
            "R180": (ox + w - x, oy + h - y)}[o]


class Plan:
    def __init__(self, path):
        self.P = json.loads(Path(path).read_text())
        self.T = self.P["partition_types"]
        self.parts = []
        for q in self.P["partitions"]:
            w, h = self.T[q["type"]]["outline_um"]
            x0, y0 = q["origin_um"]
            self.parts.append(dict(name=q["name"], type=q["type"], o=q.get("orient", "R0"), x0=x0, y0=y0, w=w, h=h,
                                   rect=(x0, y0, x0 + w, y0 + h)))
        self.cores = []          # (x0, y0, x1, y1, part, inst, module)
        for p in self.parts:
            for c in self.T[p["type"]].get("hard_cores", []):
                (cx, cy), (cw, ch) = c["origin_um"], c["outline_um"]
                a = self.to_die(p, cx, cy)
                b = self.to_die(p, cx + cw, cy + ch)
                self.cores.append((min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]), p["name"],
                                   c["inst"], c["module"]))
        self.phy = [tuple(d["rect_um"]) for d in self.P["die"]["pg"].get("domains", [])]
        self.reserve = [tuple(c["rect_um"]) for c in self.P["die"].get("channels", []) if "reserve" in c["reason"]]
        self.cbin = defaultdict(list)
        for c in self.cores:
            for i in range(int(c[0] // 200), int(c[2] // 200) + 1):
                for j in range(int(c[1] // 200), int(c[3] // 200) + 1):
                    self.cbin[(i, j)].append(c)

    def to_die(self, p, x, y):
        return tf(p["o"], p["x0"], p["y0"], p["w"], p["h"], x, y)

    def core_at(self, xy, clr=CLR):
        for c in self.cbin.get((int(xy[0] // 200), int(xy[1] // 200)), []):
            if c[0] - clr < xy[0] < c[2] + clr and c[1] - clr < xy[1] < c[3] + clr:
                return c
        return None

    def part_at(self, xy):
        for p in self.parts:
            r = p["rect"]
            if r[0] - 1e-6 <= xy[0] < r[2] - 1e-6 and r[1] - 1e-6 <= xy[1] < r[3] - 1e-6:
                return p
        for p in self.parts:     # right / top die edge of a partition
            r = p["rect"]
            if r[0] - 1e-6 <= xy[0] <= r[2] + 1e-6 and r[1] - 1e-6 <= xy[1] <= r[3] + 1e-6:
                return p
        return None


def drive_grid(PL):
    drv = []
    for p in PL.parts:
        if p["type"] == "hd_tile":
            drv.append(PL.to_die(p, 354.24, CH_Y))
    tile_cols = sorted({r3(PL.to_die(p, c, 0)[0]) for p in PL.parts if p["type"] == "hd_tile" for c in COLS_T})
    st_rows = sorted({r3(PL.to_die(p, 0, ST_ROW)[1]) for p in PL.parts if p["type"] in STATIONS})
    st_x = [(p["rect"][0], p["rect"][2]) for p in PL.parts if p["type"] in STATIONS]
    axis = sorted({r3(PL.to_die(p, 354.24, 0)[0]) for p in PL.parts if p["type"] == "hd_tile"})
    for y in st_rows:
        for x in axis:
            if any(a + 8.64 <= x <= b - 8.64 for a, b in st_x):
                drv.append((x, y))
    return sorted({(r3(x), r3(y)) for x, y in drv}), tile_cols, st_rows


def straps(PL, tile_cols, st_rows):
    """M8 rows / M9 columns of the continuous mesh as (layer, fixed, lo, hi, kind)."""
    tiles = [p for p in PL.parts if p["type"] == "hd_tile"]
    X0 = min(p["rect"][0] for p in PL.parts if p["type"] in ("hd_turn_a", "hd_turn_b"))
    X1 = max(p["rect"][2] for p in PL.parts if p["type"] in ("hd_turn_a", "hd_turn_b"))
    out = []
    for y in sorted({r3(PL.to_die(p, 0, yy)[1]) for p in tiles for yy in ROWS_T}):
        out.append(("M8", y, X0, X1, "tile_row"))
    sx0 = min(p["rect"][0] for p in PL.parts if p["type"] in STATIONS)
    sx1 = max(p["rect"][2] for p in PL.parts if p["type"] in STATIONS)
    for y in st_rows:
        out.append(("M8", y, sx0, sx1, "station_row"))
    sd = [p for p in PL.parts if p["type"] == "hd_serdes"]
    sd_rows = sorted({r3(PL.to_die(p, 0, SD_ROW)[1]) for p in sd})
    for y in sd_rows:
        out.append(("M8", y, min(p["rect"][0] for p in sd) + 8.64, max(p["rect"][2] for p in sd) - 8.64, "serdes_row"))
    ty0 = min(p["rect"][1] for p in tiles)
    ty1 = max(p["rect"][3] for p in tiles)
    for x in tile_cols:
        if sx0 + 8.64 <= x <= sx1 - 8.64:          # columns over the station band run to the serdes strip rows
            out.append(("M9", x, sd_rows[0], sd_rows[-1], "column_full"))
        else:                                       # corner reserve frames: no strap crosses them
            out.append(("M9", x, ty0 + 8.64, ty1 - 8.64, "column_array"))
    if SPINE_COLUMNS:
        # INFRA-FIRST-HEAD-4 / GEOM-REVIEW-18 on HEAD-3: the 1.74-mm spine gap between the tile column groups had
        # no M9 strap -> fill every column gap > 1.5x the tile column pitch with evenly spaced spine columns (one
        # continuous mesh, 12.8e1; no mesh-region boundary at the spine).  Same extent as the full columns.
        cols = sorted(x for L, x, *_ in out if L == "M9")
        pitch = sorted(b_ - a_ for a_, b_ in zip(cols, cols[1:]))[len(cols) // 2]
        for a_, b_ in zip(cols, cols[1:]):
            n = int(round((b_ - a_) / pitch))
            if b_ - a_ > 1.5 * pitch and n >= 2:
                for j in range(1, n):
                    out.append(("M9", r3(a_ + j * (b_ - a_) / n), sd_rows[0], sd_rows[-1], "column_spine"))
    return out, sd_rows


SPINE_COLUMNS = False


def densify_m8(S, max_pitch):
    """HEAD-CORE-R17 (COORD ruling 3): extra M8 rows so that no gap between consecutive tile-array M8 rows exceeds
    max_pitch: every gap g gets ceil(g / max_pitch) - 1 evenly spaced rows (same x extent as the tile rows).  Plan
    geometry only; the rows are then lane-snapped with the others (--pg-lanes)."""
    rows = sorted({(f, lo, hi) for L, f, lo, hi, k in S if L == "M8" and k == "tile_row"})
    out = list(S)
    for (a, lo, hi), (b, _, _) in zip(rows, rows[1:]):
        n = math.ceil((b - a) / max_pitch - 1e-9) - 1
        for j in range(1, n + 1):
            out.append(("M8", r3(a + j * (b - a) / (n + 1)), lo, hi, "tile_row_dense"))
    return out


def snap_lanes(S, plan_raw, clk_w=0.64):
    """INFRA-FIRST-HEAD-4 (opt-in --pg-lanes): move every strap to the nearest legal VSS-locked clock lane of the
    plan's die PG grid (head_pg_sweep.lanes: lane in a VSS-adjacent half-gap, wide spacing to both stripes).  Returns
    (snapped straps, per-strap jog um).  The island / driver / tap then reaches its strap through a riser of <= jog."""
    import head_pg_sweep as HP
    grid = {g["layer"]: g for g in plan_raw["die"]["pg"]["grid"] if not g.get("region")}
    out, jog = [], []
    for L, f, lo, hi, k in S:
        st = grid[L]
        ivs, _gap = HP.lanes(st, clk_w)
        if not ivs:
            raise SystemExit(f"--pg-lanes: no legal {clk_w}-um clock lane in the {L} grid {st}")
        p = st["pitch_um"]
        vss0 = st["offset_um"] + p / 2
        r = (f - vss0) % p
        best = None
        for kk in (-1, 0, 1):
            for a_, b_ in ivs:
                lo_, hi_ = a_ + kk * p, b_ + kk * p
                c = min(max(r, lo_), hi_)
                if best is None or abs(c - r) < abs(best - r):
                    best = c
        nf = r3(f + (best - r))
        out.append((L, nf, lo, hi, k))
        jog.append(r3(abs(nf - f)))
    # strap ends that sat on an end strap of the other layer follow that strap's snap (keeps the mesh one
    # component); every end is widened to cover the snapped crossing
    mv = {L: {} for L in ("M8", "M9")}
    for (L, f, *_), (_, nf, *_) in zip(S, out):
        mv[L][f] = nf
    fix = []
    for L, nf, lo, hi, k in out:
        other = mv["M9" if L == "M8" else "M8"]
        lo2, hi2 = other.get(lo, lo), other.get(hi, hi)
        fix.append((L, nf, r3(min(lo, lo2)), r3(max(hi, hi2)), k))
    return fix, jog


def on_strap(S, xy, tol=0.01):
    for L, f, lo, hi, _ in S:
        if L == "M8" and abs(xy[1] - f) <= tol and lo - tol <= xy[0] <= hi + tol:
            return True
        if L == "M9" and abs(xy[0] - f) <= tol and lo - tol <= xy[1] <= hi + tol:
            return True
    return False


def nearest_strap(S, xy):
    best = None
    for L, f, lo, hi, k in S:
        if L == "M8":
            px, py = min(max(xy[0], lo), hi), f
        else:
            px, py = f, min(max(xy[1], lo), hi)
        d = abs(px - xy[0]) + abs(py - xy[1])
        if best is None or d < best[0]:
            best = (d, L, (r3(px), r3(py)), k)
    return best


def mesh_connected(S):
    """union-find over straps: an M8 row and an M9 column are joined when they cross."""
    par = list(range(len(S)))

    def f(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i
    rows = [i for i, s in enumerate(S) if s[0] == "M8"]
    cols = [i for i, s in enumerate(S) if s[0] == "M9"]
    for i in rows:
        for j in cols:
            r, c = S[i], S[j]
            if r[2] <= c[1] <= r[3] and c[2] <= r[1] <= c[3]:
                par[f(i)] = f(j)
    return len({f(i) for i in range(len(S))})


def sites_of(nodes):
    by = {n["tag"]: n for n in nodes}
    out = []
    for n in nodes:
        out.append(("node" if n["kids"] else "driver", n["tag"], tuple(n["xy"])))
        if n.get("parent"):
            p = by[n["parent"]]["xy"]
            for k in range(1, n["nseg"]):
                out.append(("rep", n["tag"], (p[0] + (n["xy"][0] - p[0]) * k / n["nseg"],
                                              p[1] + (n["xy"][1] - p[1]) * k / n["nseg"])))
    return out


def classify(PL, xy, isl):
    c = PL.core_at(xy)
    if c is not None:
        if any(abs(xy[0] - a) <= 0.5 and abs(xy[1] - b) <= 0.5 for a, b in isl):
            return "incore_island", c[4]
        return "hard_core", c[4]
    if any(r[0] <= xy[0] <= r[2] and r[1] <= xy[1] <= r[3] for r in PL.phy):
        return "phy_zone", None
    if any(r[0] <= xy[0] <= r[2] and r[1] <= xy[1] <= r[3] for r in PL.reserve):
        return "reserve_frame", None
    p = PL.part_at(xy)
    if p is None:
        return "die_glue", None
    if p["type"] == "hd_tile":
        ly = PL.to_die(p, 0, CH_Y)[1]
        lx = PL.to_die(p, 354.24, 0)[0]
        if abs(xy[1] - ly) < 0.01:
            return "tile_channel_row", p["name"]
        if abs(xy[0] - lx) < 0.01:
            return "tile_axis_column", p["name"]
        return "tile_glue", p["name"]
    if p["type"] in ("hd_spn", "hd_spn_end"):
        return "spine_slots", p["name"]
    if p["type"] in STATIONS:
        return "station_slots", p["name"]
    return "soft_" + p["type"], p["name"]


def build_tree(drv, st_rows, et, root, step=8.64):
    """tile rows: qc_clk_mesh3.grid_tree (12 identical channel rows, y-trunk on the spine column).  Station rows: their own
    x-tree, spliced onto the y-trunk at the point (8.64 grid, both trunk halves) + arm stage count that zero the plan-model
    arrival difference (a delay-matched branch point on the trunk, not a pad: the arm is a straight vertical leg with the
    fewest stages >= reach, +0..3 stages searched; 12.8 d1 plan-computed, before any build)."""
    st_set = set(st_rows)
    tile_drv = [d for d in drv if d[1] not in st_set]
    nodes, top, info = Q.grid_tree(tile_drv, et, root=root, trunk_x=None)
    Q.ISLANDS[0], Q.BLOCK[0], Q.CORR[0], Q.LANE[0] = None, None, {}, None
    info["station_rows"] = []
    for i, y in enumerate(st_rows):
        xs = sorted(d[0] for d in drv if d[1] == y)
        sub = []
        sr = Q.dtree([(x, y) for x in xs], "x", et, f"s{i}_", sub)
        by = {n["tag"]: n for n in nodes}
        tx = info["trunk_x"]
        trunk = [n for n in nodes if n.get("parent") and abs(n["xy"][0] - tx) < 0.01
                 and abs(by[n["parent"]]["xy"][0] - tx) < 0.01]
        cands = []
        for c in trunk:
            p = by[c["parent"]]
            y0, y1 = sorted((c["xy"][1], p["xy"][1]))
            k = 0
            while y0 + k * step <= y1 + 1e-6:
                q = y0 + k * step
                if (q - y) * (c["xy"][1] - y) >= 0:      # same side of the trunk as the station row
                    cands.append((abs(q - y), c["tag"], q))
                k += 1
        best = None
        base = list(nodes)
        for _, ctag, q in sorted(cands)[:4000]:
            for extra in range(0, 4):
                trial = [dict(n) for n in base] + [dict(n) for n in sub]
                tb = {n["tag"]: n for n in trial}
                c = tb[ctag]
                p = tb[c["parent"]]
                s = dict(tag=f"S{i}", xy=(tx, q), kids=[ctag, sr["tag"]], T={}, S=0, parent=p["tag"], et=et)
                s["leg"] = abs(p["xy"][1] - q)
                s["nseg"] = et.nseg(s["leg"]) if s["leg"] > 1e-6 else 1
                p["kids"] = [s["tag"] if k_ == ctag else k_ for k_ in p["kids"]]
                c["leg"] = abs(c["xy"][1] - q)
                c["nseg"] = max(1, et.nseg(c["leg"])) if c["leg"] > 1e-6 else 1
                c["parent"] = s["tag"]
                r = tb[sr["tag"]]
                r["parent"], r["et"] = s["tag"], et
                r["leg"] = abs(q - y) + abs(r["xy"][0] - tx)
                r["nseg"] = et.nseg(r["leg"]) + extra
                trial.append(s)
                rep_, _ = Q.grid_report(trial, tb[top["tag"]])
                sk = rep_["arrival_ps"]["TT"]["skew"]
                if best is None or sk < best[0]:
                    best = (sk, trial, q, extra, rep_["arrival_ps"])
        nodes = best[1]
        top = {n["tag"]: n for n in nodes}[top["tag"]]
        info["station_rows"].append(dict(y=y, drivers=len(xs), splice_y=r3(best[2]), arm_extra_stages=best[3],
                                         skew_after_ps=best[4]))
    return nodes, top, info


def _lattice_1d(vals, pitch, centre, tol=0.05):
    """smallest power-of-two half-integer lattice about `centre` (slots centre + (j + 0.5) x pitch) holding every value;
    returns (levels, half_slots) or raises when a value is off the lattice."""
    offs = [(v - centre) / pitch for v in vals]
    for o in offs:
        if abs((o - 0.5) - round(o - 0.5)) > tol / pitch:
            raise SystemExit(f"--symmetric: value {centre + o * pitch:.3f} not on the half-integer lattice about {centre:.3f}")
    need = max(abs(o) for o in offs) + 0.5      # slots needed on each side of the centre
    L = 1
    while 2 ** (L - 1) < need - 1e-9:
        L += 1
    return L


def _h1d(nodes, et, tag, ax, fixed, centre, half, pitch, leaves, mult, tol=0.05):
    """equal-leg binary 1-D H-tree over the half-integer lattice centre +- half x pitch; empty subtrees pruned.
    leaves: {coordinate: leaf node}.  Every surviving node of one level has children at the SAME +-half/2 x pitch."""
    if half < 0.5 + 1e-9:
        for v, n in leaves.items():
            if abs(v - centre) < tol:
                return n
        return None
    kids = []
    for s, sub in (("0", -1), ("1", 1)):
        c = centre + sub * half / 2 * pitch
        k = _h1d(nodes, et, tag + s, ax, fixed, c, half / 2, pitch, leaves, mult, tol)
        if k is not None:
            kids.append(k)
    if not kids:
        return None
    xy = (centre, fixed) if ax == "x" else (fixed, centre)
    leg = half / 2 * pitch
    n = dict(tag=tag, xy=(r3(xy[0]), r3(xy[1])), kids=[k["tag"] for k in kids], T={"TT": 0.0, "FF": 0.0}, S=0, et=et,
             drive_mult=mult * len(kids), level_leg_um=r3(leg))
    for k in kids:
        k["parent"], k["leg"], k["nseg"], k["et"] = tag, leg, et.nseg(leg), et
    nodes.append(n)
    return n


def build_tree_sym(drv, st_rows, et, root, trunk_x, mult):
    """HEAD-CORE-R17 (COORD ruling 3, 12.8d / d1): SYMMETRIC re-site.  Equal legs per level BY CONSTRUCTION:
    y = one binary H on the spine column over the half-integer row lattice (tile-row pitch, centred on the tile rows;
    station driver rows re-sited onto the nearest free lattice slot inside the station band), x = per row one spine node
    with two equal legs to the mirrored half-lattice roots, then a binary H over the half-integer column lattice of each
    half.  Empty lattice slots are pruned (no dummy branch).  d1 plan-computed sizing: a node that drives ONE child
    after pruning gets half the branch-node drive (drive_mult = mult x children), so every leg sees the same driver per load.
    No measured input.  Returns (nodes, top, info, row_moves)."""
    st_set = set(st_rows)
    rows = defaultdict(list)
    for x, y in drv:
        rows[r3(y)].append(float(x))
    tile_ys = sorted(y for y in rows if y not in st_set)
    gaps = sorted(b - a for a, b in zip(tile_ys, tile_ys[1:]))
    py = gaps[len(gaps) // 2]
    yc = (tile_ys[0] + tile_ys[-1]) / 2
    Ly = _lattice_1d(tile_ys, py, yc)
    used = {round((y - yc) / py - 0.5) for y in tile_ys}
    moves = {}
    for y in sorted(st_set & set(rows)):
        o = (y - yc) / py - 0.5
        cand = sorted((abs(j - o), j) for j in range(-2 ** (Ly + 1), 2 ** (Ly + 1)) if j not in used)
        j = cand[0][1]
        used.add(j)
        moves[y] = r3(yc + (j + 0.5) * py)
    Ly = _lattice_1d(tile_ys + list(moves.values()), py, yc)      # lattice wide enough for the re-sited station rows
    allx = sorted({x for xs in rows.values() for x in xs})
    left = [x for x in allx if x < trunk_x]
    right = [x for x in allx if x > trunk_x]
    if not left or not right:
        raise SystemExit("--symmetric: drivers on one side of the spine only")
    px = sorted(b - a for a, b in zip(left, left[1:]))[(len(left) - 1) // 2]
    cl = (left[0] + left[-1]) / 2
    if round((left[-1] - left[0]) / px) % 2 == 0:      # odd column count: shift half a pitch toward the spine
        cl += px / 2
    cr = 2 * trunk_x - cl
    mir = [r3(2 * trunk_x - x) for x in right]
    if any(min(abs(m - l) for l in left) > 0.05 for m in mir):
        raise SystemExit("--symmetric: column sets are not mirror images about the spine")
    Lx = max(_lattice_1d(left, px, cl), _lattice_1d(right, px, cr))
    nodes, rroots = [], {}
    for i, y in enumerate(sorted(rows)):
        yn = moves.get(y, y)
        lv = {}
        for x in sorted(rows[y]):
            n = dict(tag=f"r{i:02d}_{x:.0f}", xy=(r3(x), yn), kids=[], T={"TT": 0.0, "FF": 0.0}, S=0, et=et, drive_mult=mult)
            nodes.append(n)
            lv[x] = n
        hl = _h1d(nodes, et, f"r{i:02d}_L", "x", yn, cl, 2 ** (Lx - 1), px, {x: n for x, n in lv.items() if x < trunk_x}, mult)
        hr = _h1d(nodes, et, f"r{i:02d}_R", "x", yn, cr, 2 ** (Lx - 1), px, {x: n for x, n in lv.items() if x > trunk_x}, mult)
        kids = [k for k in (hl, hr) if k is not None]
        rn = dict(tag=f"r{i:02d}_", xy=(r3(trunk_x), yn), kids=[k["tag"] for k in kids], T={"TT": 0.0, "FF": 0.0}, S=0, et=et,
                  drive_mult=mult * len(kids), level_leg_um=r3(abs(trunk_x - cl)))
        for k in kids:
            k["parent"], k["leg"], k["nseg"], k["et"] = rn["tag"], abs(trunk_x - cl), et.nseg(abs(trunk_x - cl)), et
        nodes.append(rn)
        rroots[yn] = rn
    top = _h1d(nodes, et, "Y", "y", trunk_x, yc, 2 ** (Ly - 1), py, rroots, mult)
    reach = set()
    st_ = [top]
    while st_:
        n = st_.pop()
        reach.add(n["tag"])
        st_.extend(m for m in nodes if m.get("parent") == n["tag"] and m["tag"] not in reach)
    lost = [n["tag"] for n in nodes if not n["kids"] and n["tag"] not in reach]
    if lost:
        raise SystemExit(f"--symmetric: {len(lost)} drivers not on the lattice tree (e.g. {lost[:3]})")
    if Q.md(top["xy"], root) > 1e-6:
        top = Q.lift(top, tuple(root), et, "SRC", nodes)
    top["parent"] = None
    # model arrivals (stage table, straight legs) for the report
    for n in nodes:
        n["T"] = {"TT": 0.0, "FF": 0.0}
        n["S"] = 0
    info = dict(form="symmetric binary H (R17)", trunk_x=r3(trunk_x), row_lattice=dict(centre=r3(yc), pitch=r3(py),
                levels=Ly), col_lattice=dict(left_centre=r3(cl), right_centre=r3(cr), pitch=r3(px), levels=Lx),
                station_row_moves={str(k): v for k, v in moves.items()},
                sizing=dict(rule="12.8 d1: drive_mult = base x children (each leg driven by base x BUFx24 = the modelled 16w stage; pruned single-child nodes half the branch-node drive)",
                            base_mult=mult, nodes_half_drive=sum(1 for n in nodes if n.get("kids") and len(n["kids"]) == 1)),
                lifted_rows=[])
    return nodes, top, info, moves


def edge_pins(PL, pins):
    """die-frame position of every real-core clock pin (R12 kit pins.json), rebuilt outline, plan origin + orient."""
    out = []
    for p in PL.parts:
        if p["type"] != "hd_tile":
            continue
        for c in PL.T["hd_tile"]["hard_cores"]:
            key = "A" if "elemA" in c["module"] else "B"
            px, py, W = pins[key]
            o = c["orient"]
            lx, ly = {"R0": (px, py), "MX": (px, W - py), "MY": (W - px, py), "R180": (W - px, W - py)}[o]
            out.append(dict(part=p["name"], inst=c["inst"], core=key, xy=PL.to_die(p, c["origin_um"][0] + lx,
                                                                                 c["origin_um"][1] + ly)))
    return out


def render(PL, S, nodes, sites, cls, path, box=None, title=""):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, ax = plt.subplots(figsize=(13, 13) if box is None else (12, 9), dpi=110)
    die = PL.P["die"]["outline_um"]
    ax.add_patch(Rectangle((0, 0), die[0], die[1], fill=False, lw=0.6))
    for p in PL.parts:
        r = p["rect"]
        ax.add_patch(Rectangle(r[:2], r[2] - r[0], r[3] - r[1], fill=False, lw=0.2, ec="0.6"))
    for c in PL.cores:
        ax.add_patch(Rectangle(c[:2], c[2] - c[0], c[3] - c[1], fc="0.85", ec="0.5", lw=0.15))
    for r in PL.phy:
        ax.add_patch(Rectangle(r[:2], r[2] - r[0], r[3] - r[1], fc="#f6e0c0", ec="none", alpha=0.6))
    for L, f, lo, hi, k in S:
        if L == "M8":
            ax.plot([lo, hi], [f, f], color="tab:blue", lw=0.35 if box is None else 0.8)
        else:
            ax.plot([f, f], [lo, hi], color="tab:cyan", lw=0.35 if box is None else 0.8)
    by = {n["tag"]: n for n in nodes}
    for n in nodes:
        if n.get("parent"):
            p = by[n["parent"]]["xy"]
            ax.plot([p[0], n["xy"][0]], [p[1], n["xy"][1]], color="tab:red", lw=0.9 if box is None else 1.6)
    col = {"rep": "k", "node": "tab:purple", "driver": "tab:green"}
    for (kind, _, xy), (c, _) in zip(sites, cls):
        bad = c in ("hard_core", "phy_zone", "reserve_frame", "tile_glue", "die_glue")
        ax.plot(*xy, marker="x" if bad else "o", ms=(2 if box is None else 4) if not bad else 6,
                color="red" if bad else col[kind], ls="none")
    if box:
        ax.set_xlim(box[0], box[2])
        ax.set_ylim(box[1], box[3])
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=9)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("plan")
    ap.add_argument("--stage", required=True)
    ap.add_argument("--pins-a", default="293.58,317.576,319.68", help="elemA clk pin x,y,outline (R12 kit pins.json)")
    ap.add_argument("--pins-b", default="0.042,257.58,285.12", help="elemB clk pin x,y,outline")
    ap.add_argument("--top-w", default="16w")
    ap.add_argument("--top-m", type=int, default=2)
    ap.add_argument("--reach", type=float, default=450.0)
    ap.add_argument("--stub-max", type=float, default=200.0, help="local-tree reach limit (12.8b core reach analogue)")
    ap.add_argument("--pg-lanes", action="store_true", help="INFRA-FIRST-HEAD-4: snap straps to the VSS-locked lanes "
                    "of the plan die.pg.grid (16W)")
    ap.add_argument("--spine-columns", action="store_true", help="INFRA-FIRST-HEAD-4: M9 straps across the spine gap")
    ap.add_argument("--symmetric", action="store_true", help="HEAD-CORE-R17: equal-leg binary H re-site (build_tree_sym)")
    ap.add_argument("--m8-max-pitch", type=float, default=0.0, help="HEAD-CORE-R17: densify tile-array M8 rows to <= this pitch (um)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    od = Path(a.out)
    od.mkdir(parents=True, exist_ok=True)
    PL = Plan(a.plan)
    drv, tile_cols, st_rows = drive_grid(PL)
    global SPINE_COLUMNS
    SPINE_COLUMNS = a.spine_columns
    S, sd_rows = straps(PL, tile_cols, st_rows)
    if a.m8_max_pitch > 0:
        S = densify_m8(S, a.m8_max_pitch)
    lane_jog = None
    if a.pg_lanes:
        S, jogs = snap_lanes(S, PL.P)
        lane_jog = dict(max_um=max(jogs), mean_um=r3(sum(jogs) / len(jogs)), straps=len(jogs),
                        rule="straps on VSS-locked lanes of die.pg.grid; risers <= max_um from island/driver/tap")
    st = Q.Stage(a.stage)
    et = Q.EdgeType(st, a.top_w, a.top_m, a.reach)
    root = tuple(PL.P["clock"]["spine"]["root_um"])
    if a.symmetric:
        nodes, top, info, moves = build_tree_sym(drv, st_rows, et, root, TRUNK_X, a.top_m)
        if moves:   # station driver rows re-sited onto lattice slots: one M8 strap per new row over the station band
            sx0 = min(p["rect"][0] for p in PL.parts if p["type"] in STATIONS)
            sx1 = max(p["rect"][2] for p in PL.parts if p["type"] in STATIONS)
            new = [("M8", y, sx0, sx1, "station_lattice_row") for y in sorted(moves.values())]
            if a.pg_lanes:
                new, j2 = snap_lanes(new, PL.P)
                shift = {v: s[1] for v, s in zip(sorted(moves.values()), new)}
                for n in nodes:   # drivers / x-tree of a moved row follow their strap's lane snap
                    if r3(n["xy"][1]) in shift:
                        n["xy"] = (n["xy"][0], shift[r3(n["xy"][1])])
                for n in nodes:
                    if n.get("parent"):
                        pxy = next(m["xy"] for m in nodes if m["tag"] == n["parent"])
                        n["leg"] = abs(pxy[0] - n["xy"][0]) + abs(pxy[1] - n["xy"][1])
                        n["nseg"] = et.nseg(n["leg"]) if n["leg"] > 1e-6 else 1
                lane_jog["max_um"] = max(lane_jog["max_um"], max(j2))
            S = S + new
            drv = sorted({(r3(n["xy"][0]), r3(n["xy"][1])) for n in nodes if not n["kids"]})
    else:
        nodes, top, info = build_tree(drv, st_rows, et, root)
    rep, arr = Q.grid_report(nodes, top)
    # ---- islands (in-core core entries, plan taps) for classification
    isl = []
    for p in PL.parts:
        for tp in PL.T[p["type"]].get("clock", {}).get("taps", []) or []:
            isl.append(PL.to_die(p, *tp["xy"]))
    sites = sites_of(nodes)
    cls = [classify(PL, xy, isl) for _, _, xy in sites]
    cnt = Counter(c for c, _ in cls)
    bad = {k: v for k, v in cnt.items() if k in ("hard_core", "phy_zone", "reserve_frame", "tile_glue", "die_glue")}
    worst = [dict(kind=k, tag=t, xy_um=[r3(xy[0]), r3(xy[1])], where=c, part=pn)
             for (k, t, xy), (c, pn) in zip(sites, cls) if c in bad][:30]
    # repeater spacing along every leg (12.1e: repeaters <= 450)
    by = {n["tag"]: n for n in nodes}
    seg_max = max((n["leg"] / n["nseg"] for n in nodes if n.get("parent")), default=0.0)
    tree_gate = dict(verdict="PASS" if not bad and seg_max <= a.reach + 1e-6 else "FAIL", sites=len(sites),
                     by_class=dict(cnt), off_site=bad, max_seg_um=r3(seg_max), reach_um=a.reach, examples=worst,
                     rule="12.2a1/12.2c + COORD RULING INFRA-FIRST-HEAD-2: every die tree node / leg repeater / mesh driver "
                          "on a declared island or channel slot (hd_tile channel row 354.24 / channel cross, spine column, "
                          "station tap row slots); none on a hard core (+1.08 clr), PHY zone, reserve frame or tile glue")
    # ---- mesh gates
    drv_on = sum(1 for d in drv if on_strap(S, d, tol=(lane_jog["max_um"] + 0.01) if lane_jog else 0.01))
    comps = mesh_connected(S)
    taps = []
    for p in PL.parts:
        ck = PL.T[p["type"]].get("clock", {})
        if ck.get("tap_um"):
            taps.append(dict(kind="partition", part=p["name"], type=p["type"], xy=PL.to_die(p, *ck["tap_um"])))
        for tp in ck.get("taps", []) or []:
            taps.append(dict(kind="core_centre_entry", part=p["name"], type=p["type"], inst=tp["name"],
                             xy=PL.to_die(p, *tp["xy"])))
        for sk in ck.get("sink_sites_um", []) or []:
            taps.append(dict(kind="density_sink", part=p["name"], type=p["type"], xy=PL.to_die(p, sk[0], sk[1])))
    pa = [float(v) for v in a.pins_a.split(",")]
    pb = [float(v) for v in a.pins_b.split(",")]
    for e in edge_pins(PL, {"A": pa, "B": pb}):
        taps.append(dict(kind="core_edge_pin_" + e["core"], part=e["part"], type="hd_tile", inst=e["inst"], xy=e["xy"]))
    stub_rows = []
    for t in taps:
        d, L, at, k = nearest_strap(S, t["xy"])
        hit = PL.core_at(t["xy"], clr=-1e-6)
        stub_rows.append(dict(t, xy=[r3(t["xy"][0]), r3(t["xy"][1])], stub_um=r3(d), strap_layer=L, strap_pt=list(at),
                              strap_kind=k))
    by_kind = defaultdict(list)
    for s in stub_rows:
        by_kind[s["kind"]].append(s["stub_um"])
    stub_sum = {k: dict(n=len(v), min=r3(min(v)), max=r3(max(v)), mean=r3(sum(v) / len(v)),
                        over_limit=sum(1 for x in v if x > a.stub_max)) for k, v in sorted(by_kind.items())}
    # edge pins: identical stub per (core type, inst slot) across instances?
    ident = defaultdict(set)
    for s in stub_rows:
        if s["kind"].startswith("core_edge_pin"):
            ident[s["inst"]].add(s["stub_um"])
    m8 = [s for s in S if s[0] == "M8"]
    m9 = [s for s in S if s[0] == "M9"]
    wire = dict(M8_um=r3(sum(s[3] - s[2] for s in m8)), M9_um=r3(sum(s[3] - s[2] for s in m9)))
    die = PL.P["die"]["outline_um"]
    # M8/M9 track share of the mesh: strap 8w 0.32 um + 0.04 shields at 0.08 spacing both sides (QC fine-mesh form)
    # = 0.32 + 2 x (0.08 + 0.04) + 0.08 = 0.64 um of pitch per strap, over the die span the straps cover (UNCHECKED)
    occ = 0.64
    share = dict(M8=r3(len(m8) * occ / die[1]), M9=r3(len(m9) * occ / die[0]),
                 basis="8w strap 0.32 + shields 0.04 @ 0.08 both sides = 0.64 um per strap / die span (UNCHECKED)")
    edge_ok = all(s["stub_um"] <= a.stub_max for s in stub_rows)
    mesh_gate = dict(
        continuity=dict(verdict="PASS" if comps == 1 else "FAIL", straps=len(S), components=comps,
                        M8_rows=len(m8), M9_cols=len(m9)),
        drivers_on_strap=dict(verdict="PASS" if drv_on == len(drv) else "FAIL", drivers=len(drv), on=drv_on),
        tap_stubs=dict(verdict="PASS" if edge_ok else "FAIL", limit_um=a.stub_max, by_kind=stub_sum,
                       edge_pin_stub_identical_per_inst={k: sorted(v) for k, v in ident.items()}),
        wire=wire, track_share=share, lane_jog=lane_jog)
    summ = dict(schema="opentallas.head_mesh_r3.v1", plan=a.plan, plan_sha256=__import__("hashlib").sha256(
        Path(a.plan).read_bytes()).hexdigest(), tree=dict(rep, **info), tree_on_islands=tree_gate, mesh=mesh_gate,
        sd_rows=sd_rows, st_rows=st_rows, note="plan model (ngspice stage-table fit); all numbers UNCHECKED")
    (od / "head_mesh_r3.json").write_text(json.dumps(summ, indent=1))
    (od / "tree_nodes.json").write_text(json.dumps([{k: v for k, v in n.items() if k != "et"} for n in nodes]))
    (od / "stubs.json").write_text(json.dumps(stub_rows))
    (od / "straps.json").write_text(json.dumps(S))
    (od / "drivers.json").write_text(json.dumps(drv))
    render(PL, S, nodes, sites, cls, od / "r3_mesh_tree.png", title="s81_head R3: channel-row tree (red) + continuous mesh "
           "M8 (blue) / M9 (cyan); drivers green, reps black, off-site red x")
    render(PL, S, nodes, sites, cls, od / "r3_zoom_spine.png", box=(6600, 7600, 10900, 10200),
           title="zoom: spine trunk x 8760.96, channel rows y0+354.24")
    render(PL, S, nodes, sites, cls, od / "r3_zoom_corner.png", box=(0, 0, 3200, 3700),
           title="zoom: SW corner, station row 1944, serdes strip row, reserve frame")
    render(PL, S, nodes, sites, cls, od / "r3_zoom_tile.png", box=(2350, 4550, 4600, 6750),
           title="zoom: 3x2 tiles, eA/eB cores grey, edge-pin stubs not drawn")
    print(json.dumps(dict(tree={k: summ["tree"][k] for k in ("drivers", "stages", "arrival_ps", "repeaters", "wire_um",
                                                              "max_merge_imbalance_ps", "lifted_rows")},
                          tree_on_islands={k: tree_gate[k] for k in ("verdict", "sites", "by_class", "max_seg_um")},
                          mesh={k: (v if k in ("wire", "track_share") else {kk: vv for kk, vv in v.items()
                                                                            if kk != "edge_pin_stub_identical_per_inst"})
                                for k, v in mesh_gate.items()}), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
