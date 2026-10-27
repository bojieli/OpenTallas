#!/usr/bin/env python3
"""QC-CLK-MESH-2 (12.8e/12.8e1 continuous die mesh, r2): shared MESH SIGN-OFF tool (COORD 17:29: owned by QC-CLK-MESH,
CLOCK-128 reviews, KV reuses).

  plan  : geometric H-tree (qc_clk_mesh.htree) to an NDX x NDY driver lattice; ONE continuous die mesh whose straps pass
          through EVERY driver-lattice row/column (both layers) plus (k-1) interpolated straps between them, so every
          driver sits on a strap crossing.  In-core points (COORD 17:42 / KV-R3 ruling): mesh drivers slide along either
          of their two straps to the nearest channel point; tree nodes re-site with EQUAL sibling legs by construction
          (sibling pairs take one common parent->child Manhattan length; internal nodes move only perpendicular to their
          own split axis so their own child legs stay equal); repeaters slide along their leg; pushdown (12.2a1) only
          where nothing is in reach.  Reports the remaining in-core count and the per-type identity check.
  deck  : ngspice deck of a WINDOW of the continuous mesh plus a guard ring of neighbour straps + drivers (measured only
          inside the window); transistor-level ASAP7 BUFx24 (per-instance DELVTRAND), plan-RC straps, MC with
          HIERARCHICAL tree variation (one Gaussian per H-tree edge, shared by every driver below it).
  solve : sparse linear RC transient of ANY deck (window or whole die) with SPICE-characterised Thevenin drivers
          (ramp source behind R_th, intrinsic delay; parameters fitted to ngspice on a window).  Runs in ot-ngspice:r3
          (scipy).
  parse : ngspice .meas of a window deck set -> skew inside the window (crossings, taps), worst over MC.
  pairs : 773 related seam pairs on the continuous mesh: flat-OCV pessimism (die_ci_margins), flat + 12.4a b1 shared
          droop, mesh uncertainty, and a HOLD-REPAIR plan-demand fragment (D_ff per seam).
All numbers produced are UNCHECKED until NUMBER-CHECK.
"""
import argparse
import hashlib
import json
import math
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

LAYER_RC = {"M8": (8.44765e-3, 1.03962e-1), "M9": (8.89556e-3, 9.28446e-2)}   # kohm/um, fF/um at 1x (die_clock.LAYER_RC)
# (R factor, C factor) vs 1x; 16w C factor extrapolated (area term ~linear in width, fringe fixed): UNCHECKED
NDR = {"2w": (0.5, 1.1), "4w": (0.25, 1.3), "8w": (0.125, 1.6), "16w": (0.0625, 2.3)}
# CLOCK-128-R6 (lanes/QC-CLK-MESH.md 18:03, COORD 18:0x): shielded 0.16-um M8/M9 R 2.115/2.228 ohm/um, C 0.188/0.194 fF/um
# (fitted rules; native plan C ~1.6x low).  8W is NOT characterised by R6: R / 2, C = 4W C x (1.6/1.3 width growth of the
# old table) x 1.13 (R6 caveat "8W still ~13 % low on C") -> conservative; 16W: R / 4, C x 2.3/1.3 x 1.13.  ohm/um, fF/um.
RC_R6 = {"4w": {"M8": (2.115, 0.188), "M9": (2.228, 0.194)},
         "8w": {"M8": (2.115 / 2, 0.188 * 1.6 / 1.3 * 1.13), "M9": (2.228 / 2, 0.194 * 1.6 / 1.3 * 1.13)},
         "16w": {"M8": (2.115 / 4, 0.188 * 2.3 / 1.3 * 1.13), "M9": (2.228 / 4, 0.194 * 2.3 / 1.3 * 1.13)}}
RC_MODE = {"mode": "r6"}
NDR_W_UM = {"2w": 0.08, "4w": 0.16, "8w": 0.32, "16w": 0.64}
VDD = {"TT": 0.70, "FF": 0.77}
ISL = 8.64
BUF_CIN_FF = 2.3


def r3(v):
    return round(float(v), 3)


def md(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def snap(v):
    return round(v / ISL) * ISL


# ------------------------------------------------------------------------------------------------ plan
def split_axis(n, by):
    kids = [m for m in by.values() if m["parent"] == n["tag"]]
    if len(kids) < 2:
        return None
    return "x" if abs(kids[0]["xy"][0] - kids[1]["xy"][0]) > 1e-6 else "y"


def channel_columns(cores, W, keep_x0, ctype):
    """centres of the vertical channels of the dominant core array (GEOM-REVIEW-7/8: qfd_tile_nk_a0c, x pitch
    622.08 / 604.8): midpoints between adjacent array columns + one half-channel outside each outer column."""
    cols = sorted({(round(c[0], 2), round(c[2], 2)) for c in cores if c[6] == ctype})
    merged = []
    for a, b in cols:
        if merged and a <= merged[-1][1] + 1.0:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    cen = [(merged[i][1] + merged[i + 1][0]) / 2 for i in range(len(merged) - 1)]
    gap = merged[1][0] - merged[0][1]
    cen = [merged[0][0] - gap / 2] + cen + [merged[-1][1] + gap / 2]
    lo = [merged[0][0] - gap] + [m[1] for m in merged]
    hi = [m[0] for m in merged] + [merged[-1][1] + gap]
    out, blocked = [], []
    for x, a, b in zip(cen, lo, hi):
        # GEOM-REVIEW-7 (COORD 18:2x): driver columns ONLY in channels free of every core over the full die height
        # (the 12 channels crossed by crh/crh_rp1, which leave < 4 ISL free beside vmr/btab, carry no driver column).
        if any(c[0] - ISL < x < c[2] + ISL for c in cores):
            blocked.append(snap(x))
            continue
        out.append(x)
    channel_columns.blocked = [x for x in blocked if keep_x0 <= x <= W]
    return [snap(x) for x in out if keep_x0 <= x <= W], merged


def gtree(cols, rows, stage):
    """balanced, equal-structure tree over leaves cols x rows (any counts, not only pow2).  Split the axis with more
    leaves into floor/ceil halves; the node sits on the segment between the two child roots at the point where both
    root->leaf Manhattan lengths are equal (x0 = (xa + xb + T(b) - T(a)) / 2, no detour); sibling legs get repeater
    counts so that every root->leaf path has the same stage count (n >= ceil(leg / 450)).  Every root->leaf path then
    has the same wire length AND stage count -> equal delay at every corner by construction (12.8 d/d1)."""
    nodes = []

    def rec(cs, rs, tag, depth):
        if len(cs) == 1 and len(rs) == 1:
            n = dict(tag=tag, depth=depth, xy=(cs[0], rs[0]), kids=[], ax=None, T=0.0, S=0)
            nodes.append(n)
            return n
        ax = "x" if len(cs) >= len(rs) else "y"
        if ax == "x":
            h = len(cs) // 2
            A, Bn = rec(cs[:h], rs, tag + "0", depth + 1), rec(cs[h:], rs, tag + "1", depth + 1)
            pa, pb = A["xy"][0], Bn["xy"][0]
        else:
            h = len(rs) // 2
            A, Bn = rec(cs, rs[:h], tag + "0", depth + 1), rec(cs, rs[h:], tag + "1", depth + 1)
            pa, pb = A["xy"][1], Bn["xy"][1]
        p0 = (pa + pb + Bn["T"] - A["T"]) / 2.0
        assert pa - 1e-6 <= p0 <= pb + 1e-6, (tag, pa, pb, A["T"], Bn["T"])
        xy = (p0, A["xy"][1]) if ax == "x" else (A["xy"][0], p0)
        la, lb = md(xy, A["xy"]), md(xy, Bn["xy"])
        na = max(math.ceil(la / 450.0 - 1e-9), math.ceil(lb / 450.0 - 1e-9) + Bn["S"] - A["S"], 1)
        nb = na + A["S"] - Bn["S"]
        if nb < max(1, math.ceil(lb / 450.0 - 1e-9)):
            nb = max(1, math.ceil(lb / 450.0 - 1e-9))
            na = nb + Bn["S"] - A["S"]
        A["nseg"], Bn["nseg"] = na, nb
        n = dict(tag=tag, depth=depth, xy=xy, kids=[A["tag"], Bn["tag"]], ax=ax, T=la + A["T"], S=na + A["S"])
        for c in (A, Bn):
            c["parent"] = tag
        nodes.append(n)
        return n
    root = rec(cols, rows, "h", 0)
    root["parent"] = None
    by = {n["tag"]: n for n in nodes}
    return sorted(nodes, key=lambda n: n["depth"]), by


def row_gaps(cores, H, ctype):
    rows = sorted({(round(c[1], 2), round(c[3], 2)) for c in cores if c[6] == ctype})
    merged = []
    for a, b in rows:
        if merged and a <= merged[-1][1] + 1.0:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    gaps = [(merged[i][1] + merged[i + 1][0]) / 2 for i in range(len(merged) - 1)]
    g = merged[1][0] - merged[0][1]
    gaps = [merged[0][0] - g / 2] + gaps + [merged[-1][1] + g / 2]
    gaps = sorted(y for y in gaps if 0 < y < H)
    med = sorted(b - a for a, b in zip(gaps, gaps[1:]))[len(gaps) // 2]
    out = [gaps[0]]
    for a, b in zip(gaps, gaps[1:]):            # bands without the array (mid band): extra groups at ~the array pitch
        k = max(1, round((b - a) / med))
        out += [a + (b - a) * q / k for q in range(1, k)] + [b]
    return [snap(y) for y in out], merged


def gtree_gap(cols, gaps, dy, H, m=1, xok=None):
    """GEOM-REVIEW-7/8 commensurate tree: driver columns = nk channel centres; driver rows = 3 per nk row gap
    (gap - dy, gap, gap + dy).  Order: y-tree over gap groups (on one vertical channel x0) -> per group an x-tree
    ALONG the gap row (horizontal channel) -> per column a 3-row y-tree in the vertical channel.  Every node uses the
    equal-length placement of gtree (no detour), every path the same stage count."""
    nodes = []

    def mk(tag, xy, kids, ax, T, S):
        n = dict(tag=tag, xy=xy, kids=[k["tag"] for k in kids], ax=ax, T=T, S=S)
        for k in kids:
            k["parent"] = tag
        nodes.append(n)
        return n

    def join(tag, A, Bn, ax):
        pa, pb = (A["xy"][0], Bn["xy"][0]) if ax == "x" else (A["xy"][1], Bn["xy"][1])
        e = abs(A["xy"][1] - Bn["xy"][1]) if ax == "x" else abs(A["xy"][0] - Bn["xy"][0])
        p0 = (pa + pb + Bn["T"] + e - A["T"]) / 2.0
        p0 = min(max(p0, pa), pb)
        xy = (p0, A["xy"][1]) if ax == "x" else (A["xy"][0], p0)
        la, lb = md(xy, A["xy"]), md(xy, Bn["xy"])
        na = max(math.ceil(la / 450.0 - 1e-9), math.ceil(lb / 450.0 - 1e-9) + Bn["S"] - A["S"], 1)
        nb = na + A["S"] - Bn["S"]
        if nb < max(1, math.ceil(lb / 450.0 - 1e-9)):
            nb = max(1, math.ceil(lb / 450.0 - 1e-9))
            na = nb + Bn["S"] - A["S"]
        A["nseg"], Bn["nseg"] = na, nb
        return mk(tag, xy, [A, Bn], ax, la + A["T"], na + A["S"])

    def tree(items, tag, ax, leaf):
        if len(items) == 1:
            return leaf(items[0], tag)
        h = len(items) // 2
        return join(tag, tree(items[:h], tag + "0", ax, leaf), tree(items[h:], tag + "1", ax, leaf), ax)

    def col_tree(x, rows, tag):
        return tree(rows, tag, "y", lambda y, t: mk(t, (x, y), [], None, 0.0, 0))

    def group(g, tag):
        rows = [g + j * dy for j in range(-m, m + 1)] if (g - m * dy > 0 and g + m * dy < H) else [g]   # edge gap: one row ON the gap
        leaf = lambda x, t: col_tree(x, rows, t)
        if xok is None or len(cols) < 2:
            return tree(cols, tag, "x", leaf)
        # the group root carries the top y-tree (vertical, crosses every array row), so the top y-tree runs in the
        # free channel (GEOM-REVIEW-7) nearest the equal-length group root x0; each group joins it by one horizontal
        # leg ALONG its gap row (x0 -> xc, same length for every group, so equal length/stages are kept).
        r = tree(cols, tag + "0", "x", leaf)
        x0 = r["xy"][0]
        if xok(x0):
            return r
        xc = min(cols, key=lambda x: abs(x - x0))
        L = abs(xc - x0)
        r["nseg"] = max(1, math.ceil(L / 450.0 - 1e-9))
        return mk(tag, (xc, r["xy"][1]), [r], "x", L + r["T"], r["nseg"] + r["S"])
    root = tree(gaps, "h", "y", group)
    root["parent"] = None
    by = {n["tag"]: n for n in nodes}
    for n in nodes:
        d, t = 0, n
        while t.get("parent"):
            d += 1
            t = by[t["parent"]]
        n["depth"] = d
    return sorted(nodes, key=lambda n: n["depth"]), by


def build_plan(P, parts, cores, entries, trunk, cols, rows, kx, ky, smax, stage, gaps=None, dy=None, gm=1, tap_at_driver=False):
    import region_clock as RC
    legal = RC.Legal(parts, cores)
    if gaps:
        nodes, by = gtree_gap(cols, gaps, dy, P.H, gm, xok=lambda x: not any(c[0] - ISL < x < c[2] + ISL for c in cores))
        rows = sorted({n["xy"][1] for n in nodes if not n["kids"]})
    else:
        nodes, by = gtree(cols, rows, stage)
    drv = [n for n in nodes if not n["kids"]]

    def fill(c, k, adapt=False):
        out = []
        pitch = min(b - a for a, b in zip(c, c[1:])) / k     # keep the strap pitch where a blocked column was dropped
        for a, b in zip(c, c[1:]):
            kk = max(k, round((b - a) / pitch)) if adapt else k
            out += [snap(a + (b - a) * q / kk) for q in range(kk)]
        return sorted(set(out + [c[-1]]))
    xs, ys = fill(sorted(cols), kx, True), fill(sorted(rows), ky, False)

    def ok(q):          # partition glue OR a partition-seam channel cross (12.2a die infra island), never on a core
        return legal.part(q, -ISL / 2) is not None and legal.in_core(q, ISL / 2) is None

    def core_of(q):
        c = legal.in_core(q, ISL / 2)
        return dict(type=c[6], inst=c[5], off=[r3(q[0] - c[0]), r3(q[1] - c[1])]) if c else None
    # sites: ideal (plan-exact, NOT snapped: the lattice is already commensurate); an in-core LEAF slides along its
    # channel strap (M9, x fixed) with its sibling taking the same leg (equal legs by construction); an in-core
    # internal node moves only perpendicular to its own split axis, sibling pair with a common leg.
    for n in nodes:
        n["site"], n["disp_um"] = n["xy"], 0.0
    # in-core INTERNAL node: move inside the monotone box of its parent and every child (md(p,q)+md(q,c) = md(p,c)), so
    # no root->leaf length changes (equal legs by construction kept); child legs must still fit their repeater count.
    mism = []
    for n in nodes:
        if n["parent"] is None or not n["kids"] or ok(n["site"]):
            continue
        ps = by[n["parent"]]["site"]
        X, Y = n["site"]
        R = int(smax / ISL)
        best = None
        for r in range(1, R + 1):
            for di in range(-r, r + 1):
                for dj in {r - abs(di), -(r - abs(di))}:
                    q = (X + di * ISL, Y + dj * ISL)
                    if not ok(q):
                        continue
                    if any(abs(md(ps, q) + md(q, by[c]["site"]) - md(ps, by[c]["site"])) > 1e-6 for c in n["kids"]):
                        continue
                    if any(math.ceil(md(q, by[c]["site"]) / 450.0 - 1e-9) > by[c]["nseg"] for c in n["kids"]):
                        continue
                    best = (q, r * ISL)
                    break
                if best:
                    break
            if best:
                break
        if best:
            n["site"], n["disp_um"] = best
    for n in nodes:
        n["binding"] = ("channel" if legal.part(n["site"], ISL / 2) is not None else "seam_channel") if ok(n["site"]) else ("in_core_pushdown" if legal.in_core(n["site"], ISL / 2) else "glue_pushdown_request")
        if n["binding"] == "in_core_pushdown":
            n["core"] = core_of(n["site"])
    reps = []

    def leg_path(p, q):
        return [p, (q[0], p[1]), q]

    def at(path, s):
        for u, v in zip(path, path[1:]):
            L = md(u, v)
            if s <= L + 1e-9:
                f = s / L if L else 0
                return (u[0] + (v[0] - u[0]) * f, u[1] + (v[1] - u[1]) * f)
            s -= L
        return path[-1]
    root = nodes[0]
    for n in nodes:
        if n["parent"] is None:
            n["arr"] = {c: stage[c][0] * trunk["n_seg"] + stage[c][1] * trunk["len_um"] for c in ("TT", "FF")}
            n["leg_um"], n["nseg"] = 0.0, 0
            continue
        p = by[n["parent"]]
        L = md(p["site"], n["site"])
        nseg = max(n["nseg"], math.ceil(L / 450.0 - 1e-9))
        n["nseg"], n["leg_um"] = nseg, r3(L)
        n["leg_exact"] = L
        n["arr"] = {c: p["arr"][c] + nseg * stage[c][0] + stage[c][1] * L for c in ("TT", "FF")}
        placed = None
        for path in ([p["site"], (n["site"][0], p["site"][1]), n["site"]], [p["site"], (p["site"][0], n["site"][1]), n["site"]]):
            pts = [s_ * ISL for s_ in range(0, int(L / ISL) + 1)]
            legal_s = [s_ for s_ in pts if 0 < s_ < L and ok(at(path, s_))]
            ideal = [L * r / nseg for r in range(1, nseg)]
            chosen, prev, okk = [], 0.0, True
            for r, s0 in enumerate(ideal):
                # nearest legal point to the ideal one that keeps the gap <= 450 and leaves the rest feasible
                rem = nseg - 1 - r
                cand = [s_ for s_ in legal_s if prev < s_ <= prev + 450.0 and L - s_ <= 450.0 * (rem + 1) - 1e-6]
                if not cand:
                    okk = False
                    break
                s_ = min(cand, key=lambda v: abs(v - s0))
                chosen.append(s_)
                prev = s_
            if okk and L - prev <= 450.0 + 1e-6:
                placed = (path, chosen)
                break
        if placed:
            path, chosen = placed
            for s_ in chosen:
                q = at(path, s_)
                reps.append(dict(leg=n["tag"], site=[r3(q[0]), r3(q[1])], binding="channel", core=None))
        else:
            path = leg_path(p["site"], n["site"])
            for r in range(1, nseg):
                q = at(path, L * r / nseg)
                bind = "channel" if ok(q) else ("in_core_pushdown" if legal.in_core(q, ISL / 2) else "glue_pushdown_request")
                reps.append(dict(leg=n["tag"], site=[r3(q[0]), r3(q[1])], binding=bind,
                                 core=core_of(q) if bind == "in_core_pushdown" else None))
    taps = []
    dsites = [n["site"] for n in drv if ok(n["site"])]
    for e in entries:
        ex, ey = e["xy_um"]
        X = min(xs, key=lambda x: abs(x - ex))
        Y = min(ys, key=lambda y: abs(y - ey))
        site = (X, Y)
        if tap_at_driver:      # tap = the mesh point AT the nearest driver (uniform nominal arrival across taps)
            site = min(dsites, key=lambda q: md(q, (ex, ey)))
        if not ok(site):
            best = None
            for s in range(1, int(smax / ISL) + 1):
                for q in ((X, Y + s * ISL), (X, Y - s * ISL), (X + s * ISL, Y), (X - s * ISL, Y)):
                    if ok(q) and (q[0] in xs or q[1] in ys):
                        best = q
                        break
                if best:
                    break
            site = best or site
        taps.append(dict(part=e["part"], entry=e["xy_um"], tap=[r3(site[0]), r3(site[1])], stub_um=r3(md(site, e["xy_um"])),
                         binding="channel" if ok(site) else "in_core_pushdown"))
    return dict(nodes=nodes, by=by, drivers=drv, xs=xs, ys=ys, reps=reps, taps=taps,
                sib_mismatch_um=max(mism) if mism else 0.0)


def identity(items):
    """12.2a1: per core type, every instance must carry the same island offset set."""
    per = defaultdict(lambda: defaultdict(set))
    for it in items:
        c = it.get("core")
        if c:
            per[c["type"]][c["inst"]].add(tuple(c["off"]))
    out = {}
    for t, insts in per.items():
        sets = {frozenset(v) for v in insts.values()}
        out[t] = dict(instances_hit=len(insts), distinct_offset_sets=len(sets), identical=len(sets) == 1)
    return out


def cmd_plan(a):
    import qc_clk_mesh as Q
    P, dtp, parts, cores, psha = Q.load(a.plan, a.tree_plan)
    stage = json.loads(a.stage) if a.stage else {c: list(v) for c, v in Q.STAGE.items()}
    cols, arr_cols = channel_columns(cores, P.W, a.keepout_x, a.array_type)
    import region_clock as RC
    lg = RC.Legal(parts, cores)
    # a channel centre on a partition seam: move one lattice step into the partition that owns more of the channel
    for i, x in enumerate(cols):
        ys_ = [P.H * (j + 0.5) / 40 for j in range(40)]
        if sum(lg.part((x, y), ISL / 2) is not None for y in ys_) < 20:
            for dx in (ISL, -ISL, 2 * ISL, -2 * ISL):
                if sum(lg.part((x + dx, y), ISL / 2) is not None for y in ys_) >= 20:
                    cols[i] = x + dx
                    break
    gaps = None
    if a.rows == "gaps":
        gaps, _ = row_gaps(cores, P.H, a.array_type)
        # die-edge "gap" (y ~ 0: the array starts 78 um above the die edge) cannot hold a full row group; its lone row
        # left a 734-um undriven strap span (whole-die solve: +46 ps late edge row) -> drop, as at the top edge.
        gaps = [g for g in gaps if a.gap_m * a.gap_dy < g < P.H - a.gap_m * a.gap_dy]
        rows, ny = [], 0
    else:
        ny = int(a.rows)
        rows = [snap(P.H * (j + 0.5) / ny) for j in range(ny)]
    B = build_plan(P, parts, cores, dtp["regions"]["entries"], dtp["lattice"]["trunk"], cols, rows, a.kx, a.ky,
                   a.slide_max, stage, gaps=gaps, dy=a.gap_dy, gm=a.gap_m, tap_at_driver=a.tap_at_driver)
    ny = len({tuple(d["site"])[1] for d in B["drivers"]}) if gaps else ny
    drv = B["drivers"]
    tree = [n for n in B["nodes"] if n["kids"] and n["parent"] is not None]
    cnt = lambda L: {b: sum(1 for x in L if x.get("binding") == b) for b in ("channel", "seam_channel", "in_core_pushdown", "glue_pushdown_request")}
    arr = {c: [d["arr"][c] for d in drv] for c in ("TT", "FF")}
    slides = [d.get("disp_um", 0.0) for d in drv]
    rec = dict(schema="ot_qc_clk_mesh2/1", plan=a.plan, plan_sha256=psha, tree_plan=a.tree_plan, argv=sys.argv,
               W=P.W, H=P.H, drivers="%dx%d" % (len(cols), ny), k=[a.kx, a.ky], ndr=a.ndr, array_type=a.array_type,
               array_columns=len(arr_cols), driver_columns=cols, blocked_channels=getattr(channel_columns, 'blocked', []), keepout_x_um=a.keepout_x, stage=stage, slide_max_um=a.slide_max,
               straps=dict(M9_vertical=len(B["xs"]), M8_horizontal=len(B["ys"]),
                           pitch_x_um=r3((B["xs"][-1] - B["xs"][0]) / (len(B["xs"]) - 1)),
                           pitch_y_um=r3((B["ys"][-1] - B["ys"][0]) / (len(B["ys"]) - 1))),
               xs=B["xs"], ys=B["ys"],
               counts=dict(drivers=cnt(drv), tree_nodes=cnt(tree), repeaters=cnt(B["reps"]), taps=cnt(B["taps"])),
               in_core_total=sum(1 for x in drv + tree + B["reps"] if x.get("binding") in ("in_core_pushdown", "glue_pushdown_request")),
               identity=identity(drv + tree + B["reps"]),
               driver_slide_um=dict(max=r3(max(slides)), mean=r3(sum(slides) / len(slides)), moved=sum(1 for s in slides if s > 0)),
               sibling_leg_mismatch_um_max=r3(B["sib_mismatch_um"] * ISL if False else B["sib_mismatch_um"]),
               insertion_die_input_to_driver={c: dict(min=r3(min(v)), max=r3(max(v)), spread=r3(max(v) - min(v))) for c, v in arr.items()},
               tree=dict(levels=max(n["depth"] for n in B["nodes"]), repeaters=len(B["reps"]),
                         root_to_driver_um=dict(min=r3(min(sum(B["by"][t]["leg_um"] for t in chain(B["by"], d["tag"])) for d in drv)),
                                                max=r3(max(sum(B["by"][t]["leg_um"] for t in chain(B["by"], d["tag"])) for d in drv))),
                         stages_root_to_driver=sorted({sum(B["by"][t]["nseg"] for t in chain(B["by"], d["tag"])) for d in drv})),
               nodes=[dict(tag=n["tag"], parent=n["parent"], site=[r3(v) for v in n["site"]], leg_um=n["leg_um"], arr=n["arr"],
                           binding=n.get("binding"), driver=not n["kids"], core=n.get("core")) for n in B["nodes"]],
               reps=B["reps"], taps=B["taps"], checked="UNCHECKED (plan model; NUMBER-CHECK)")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "r2_plan.json").write_text(json.dumps(rec, indent=1, default=str))
    s = {k: rec[k] for k in ("straps", "counts", "in_core_total", "driver_slide_um", "sibling_leg_mismatch_um_max",
                             "insertion_die_input_to_driver", "tree")}
    s["identity_fail_types"] = [t for t, v in rec["identity"].items() if not v["identical"]]
    print(json.dumps(s, indent=1))
    if not a.no_render:
        render(P, parts, cores, rec, out / "r2_plan.png", None)
        cx, cy = P.W / 2, P.H / 2
        render(P, parts, cores, rec, out / "r2_zoom_centre.png", (cx - 1500, cy - 1200, cx + 1500, cy + 1200))
    return 0


def chain(by, tag):
    out, t = [], tag
    while t is not None and by[t]["parent"] is not None:
        out.append(t)
        t = by[t]["parent"]
    return out


def render(P, parts, cores, rec, path, box):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, ax = plt.subplots(figsize=(16, 13.5))
    for p in parts:
        ax.add_patch(Rectangle((p[0], p[1]), p[2] - p[0], p[3] - p[1], fill=False, lw=0.3, ec="#999999"))
    for c in cores:
        ax.add_patch(Rectangle((c[0], c[1]), c[2] - c[0], c[3] - c[1], fc="#e4e4e4", ec="none"))
    xs, ys = rec["xs"], rec["ys"]
    lw = 0.15 if box is None else 0.6
    for x in xs:
        ax.plot([x, x], [ys[0], ys[-1]], "-", c="#7fb3ff", lw=lw)
    for y in ys:
        ax.plot([xs[0], xs[-1]], [y, y], "-", c="#9fd39f", lw=lw)
    by = {n["tag"]: n for n in rec["nodes"]}
    for n in rec["nodes"]:
        if n["parent"] is None:
            continue
        p, q = by[n["parent"]]["site"], n["site"]
        d = len(n["tag"]) - 1
        ax.plot([p[0], q[0], q[0]], [p[1], p[1], q[1]], "-", c="k", lw=0.4 + 2.5 * (1 - d / 12))
    col = {"channel": "#c00000", "seam_channel": "#a05000", "in_core_pushdown": "#ff00ff", "glue_pushdown_request": "#ff8c00"}
    for b, cc in col.items():
        pts = [n["site"] for n in rec["nodes"] if n["driver"] and n["binding"] == b]
        if pts:
            ax.plot([p[0] for p in pts], [p[1] for p in pts], "s", ms=2.0 if box is None else 5, c=cc,
                    label=f"driver {b} ({len(pts)})")
    pts = [r["site"] for r in rec["reps"] if r["binding"] != "channel"]
    if pts:
        ax.plot([p[0] for p in pts], [p[1] for p in pts], "x", ms=3, c="#ff00ff", label=f"repeater in core ({len(pts)})")
    ax.plot([t["tap"][0] for t in rec["taps"]], [t["tap"][1] for t in rec["taps"]], "o", ms=3, mfc="none", c="#008000",
            label=f"tap ({len(rec['taps'])})")
    ax.set_aspect("equal")
    if box:
        ax.set_xlim(box[0], box[2])
        ax.set_ylim(box[1], box[3])
    else:
        ax.set_xlim(0, rec["W"])
        ax.set_ylim(0, rec["H"])
    ax.legend(loc="upper right", fontsize=8)
    ax.set_title(f"QC-CLK-MESH-2 r2: continuous die mesh {len(xs)} M9 x {len(ys)} M8 straps ({rec['ndr']}), drivers "
                 f"{rec['drivers']} on nk channel columns at strap crossings (k={rec['k']}), H-tree black. UNCHECKED", fontsize=10)
    fig.savefig(path, dpi=110 if box else 100, bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------------------------------------ netlist / deck
def netlist(rec, corner, box=None, ring_um=0.0, seg_um=54.0, sigma=None, seed=0, ndr=None, drv_mult=1):
    """mesh RC + drivers + taps inside box (+ring).  Returns dict(R=[(a,b,ohm)], C={node:fF}, drv=[...], taps=[...],
    xnodes={(i,j):node} measured crossings (inside box only))."""
    ndr = ndr or rec["ndr"]
    rf, cf = NDR[ndr]
    xs, ys = [r3(x) for x in rec["xs"]], [r3(y) for y in rec["ys"]]
    if box:
        bx = (box[0] - ring_um, box[1] - ring_um, box[2] + ring_um, box[3] + ring_um)
    else:
        bx = (xs[0] - 1, ys[0] - 1, xs[-1] + 1, ys[-1] + 1)
    inb = lambda q, b: b[0] <= q[0] <= b[2] and b[1] <= q[1] <= b[3]
    X = [x for x in xs if bx[0] <= x <= bx[2]]
    Y = [y for y in ys if bx[1] <= y <= bx[3]]
    xl, xh = max(bx[0], xs[0]), min(bx[2], xs[-1])
    yl, yh = max(bx[1], ys[0]), min(bx[3], ys[-1])
    rnd = random.Random(1000 * seed + 17)
    sg = sigma or {}
    by = {n["tag"]: n for n in rec["nodes"]}
    # hierarchical tree variation: one Gaussian per H-tree edge, sigma = s_stage * sqrt(stages of the edge)
    off = {}
    if seed and sg.get("tree_ps_per_stage"):
        for n in sorted(rec["nodes"], key=lambda n: len(n["tag"])):
            if n["parent"] is None:
                off[n["tag"]] = 0.0
                continue
            nst = max(1, math.ceil(n["leg_um"] / 450.0 - 1e-9))
            off[n["tag"]] = off[n["parent"]] + rnd.gauss(0.0, sg["tree_ps_per_stage"] * math.sqrt(nst))
    hp, vp = defaultdict(set), defaultdict(set)      # attach points per strap
    for y in Y:
        hp[y] |= set(X) | {xl, xh}
    for x in X:
        vp[x] |= set(Y) | {yl, yh}
    drv = []
    for n in rec["nodes"]:
        if not n["driver"]:
            continue
        q = (r3(n["site"][0]), r3(n["site"][1]))
        if not inb(q, (xl, yl, xh, yh)):
            continue
        if q[1] in hp:
            hp[q[1]].add(q[0])
            key = ("H", q[1], q[0])
        elif q[0] in vp:
            vp[q[0]].add(q[1])
            key = ("V", q[0], q[1])
        else:
            raise SystemExit(f"driver {n['tag']} at {q} is not on a strap")
        drv.append(dict(tag=n["tag"], key=key, arr=n["arr"][corner] + off.get(n["tag"], 0.0),
                        dvn=[rnd.gauss(0, sg.get("vt_mV", 0) / 1e3) if seed else 0.0 for _ in range(drv_mult)],
                        dvp=[rnd.gauss(0, sg.get("vt_mV", 0) / 1e3) if seed else 0.0 for _ in range(drv_mult)]))
    taps = []
    for t in rec["taps"]:
        q = (r3(t["tap"][0]), r3(t["tap"][1]))
        if not inb(q, (xl, yl, xh, yh)):
            continue
        if q[1] in hp:
            hp[q[1]].add(q[0])
            key = ("H", q[1], q[0])
        elif q[0] in vp:
            vp[q[0]].add(q[1])
            key = ("V", q[0], q[1])
        else:
            continue
        taps.append(dict(part=t["part"], key=key, stub_um=t["stub_um"], inside=box is None or inb(q, box),
                         dvn=rnd.gauss(0, sg.get("vt_mV", 0) / 1e3) if seed else 0.0,
                         dvp=rnd.gauss(0, sg.get("vt_mV", 0) / 1e3) if seed else 0.0))

    def canon(k):
        if k[0] == "H" and k[2] in vp:
            return ("X", k[2], k[1])
        if k[0] == "V" and k[2] in hp:
            return ("X", k[1], k[2])
        return k
    nid = {}

    def node(k):
        k = canon(k)
        if k not in nid:
            nid[k] = "n%d" % len(nid)
        return nid[k]
    R, C = [], defaultdict(float)
    wr = sg.get("wire_rel", 0.0) if seed else 0.0

    def wire(ka, kb, L, layer):
        if RC_MODE["mode"] == "r6":
            r, c = RC_R6[ndr][layer]
        else:
            r, c = LAYER_RC[layer]
            r, c = r * rf * 1e3, c * cf
        n = max(1, int(math.ceil(L / seg_um)))
        prev = node(ka)
        for q in range(1, n + 1):
            cur = node(kb) if q == n else node((ka, kb, q))
            f = rnd.gauss(1.0, wr) if wr else 1.0
            R.append((prev, cur, r * L / n * f))
            C[prev] += c * L / n / 2 * f
            C[cur] += c * L / n / 2 * f
            prev = cur
    for y, pts in hp.items():
        p = sorted(pts)
        for u, w in zip(p, p[1:]):
            wire(("H", y, u), ("H", y, w), w - u, "M8")
    for x, pts in vp.items():
        p = sorted(pts)
        for u, w in zip(p, p[1:]):
            wire(("V", x, u), ("V", x, w), w - u, "M9")
    for d in drv:
        d["node"] = node(d["key"])
    for t in taps:
        t["node"] = node(t["key"])
        C[t["node"]] += BUF_CIN_FF
    meas_box = box or bx
    xnodes = {(x, y): nid[("X", x, y)] for x in X for y in Y if ("X", x, y) in nid and inb((x, y), meas_box)}
    return dict(R=R, C=C, drv=drv, taps=taps, xnodes=xnodes, nodes=len(nid), box=bx, meas_box=meas_box,
                drivers_in_meas=sum(1 for d in drv if inb((d["key"][2], d["key"][1]) if d["key"][0] == "H" else (d["key"][1], d["key"][2]), meas_box)))


def write_deck(N, corner, path, drv_mult=1, t_end=None):
    t0 = min(d["arr"] for d in N["drv"])
    span = max(d["arr"] for d in N["drv"]) - t0
    t_end = t_end or (span + 700.0)
    L = [f"* QC-CLK-MESH-2 window deck {corner}", f".param vdd={VDD[corner]}", ".temp %s" % ({"TT": 25.0, "FF": 0.0}[corner]),
         f".include /w/lib/{corner}/models.sp", f".include /w/lib/{corner}/cells_var.sp", "Vdd vdd 0 {vdd}", "Vss vss 0 0",
         "Vref ref 0 PWL(0 0 100p 0 150p {vdd})"]
    for i, (a, b, r) in enumerate(N["R"]):
        L.append(f"R{i} {a} {b} {r:.4f}")
    for k, d in enumerate(N["drv"]):
        st = 100.0 + d["arr"] - t0
        L.append(f"Vin{k} in{k} 0 PWL(0 0 {st:.3f}p 0 {st + 50.0:.3f}p {{vdd}})")
        L.append(f"Rd{k} d{k} {d['node']} 51.2")      # via stack M1->M9 (die_clock_mesh convention)
        for q in range(drv_mult):
            L.append(f"Xd{k}_{q} vss vdd in{k} d{k} BUFx24v dvn={d['dvn'][q]:.5f} dvp={d['dvp'][q]:.5f}")
    for k, t in enumerate(N["taps"]):
        L.append(f"Xt{k} vss vdd {t['node']} to{k} BUFx24v dvn={t['dvn']:.5f} dvp={t['dvp']:.5f}")
        L.append(f"Ct{k} to{k} 0 30f")
    for k, v in N["C"].items():
        L.append(f"C{k} {k} 0 {v:.5f}f")
    for k, t in enumerate(N["taps"]):
        if t["inside"]:
            L.append(f".meas tran tm{k} TRIG v(ref) VAL={{vdd/2}} RISE=1 TARG v({t['node']}) VAL={{vdd/2}} RISE=1")
    for (x, y), nn in N["xnodes"].items():
        L.append(f".meas tran x_{x:.2f}_{y:.2f} TRIG v(ref) VAL={{vdd/2}} RISE=1 TARG v({nn}) VAL={{vdd/2}} RISE=1".replace(".", "p", 0))
    L.append(".options method=gear reltol=1e-4 abstol=1e-12 vntol=1e-7")
    L.append(f".tran 0.5p {t_end:.0f}p 0 0.5p")
    L.append(".control\npre_osdi /w/osdi/bsimcmg23.osdi\nrun\nquit\n.endc\n.end")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(L) + "\n")
    return dict(t0=t0, span=span)


def cmd_deck(a):
    rec = json.loads(Path(a.r2).read_text())
    box = [float(v) for v in a.window.split(",")]
    sigma = json.loads(a.sigma)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    meta = dict(rc=a.rc, rc_table=RC_R6 if a.rc == "r6" else "plan LAYER_RC x NDR", window=box, ring_um=a.ring, corner=a.corner, ndr=a.ndr or rec["ndr"], sigma=sigma, samples=a.samples,
                drv_mult=a.drv_mult, r2=a.r2, decks=[])
    for s in range(a.samples + 1):
        N = netlist(rec, a.corner, box, a.ring, sigma=sigma, seed=s, ndr=a.ndr, drv_mult=a.drv_mult)
        info = write_deck(N, a.corner, out / f"s{s:03d}" / "deck.sp", drv_mult=a.drv_mult)
        meta["decks"].append(dict(sample=s, nodes=N["nodes"], resistors=len(N["R"]), drivers=len(N["drv"]),
                                  drivers_in_window=N["drivers_in_meas"], taps_in_window=sum(t["inside"] for t in N["taps"]),
                                  crossings_in_window=len(N["xnodes"]), **info))
        meta["tap_parts"] = [t["part"] for t in N["taps"] if t["inside"]]
    (out / "meta.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps(meta["decks"][0]))
    return 0


def parse_log(f):
    v = {}
    for m in re.finditer(r"^(tm\d+|x_\S+)\s*=\s*([-+0-9.eE]+)", Path(f).read_text(), re.M):
        v[m.group(1)] = float(m.group(2)) * 1e12
    return v


def cmd_parse(a):
    d = Path(a.dir)
    meta = json.loads((d / "meta.json").read_text())
    res = []
    for s in sorted(d.glob("s[0-9][0-9][0-9]")):
        f = s / "sim.log"
        if not f.exists():
            continue
        v = parse_log(f)
        tm = [x for k, x in v.items() if k.startswith("tm")]
        xc = [x for k, x in v.items() if k.startswith("x_")]
        if not xc:
            res.append(dict(sample=s.name, error="no meas"))
            continue
        res.append(dict(sample=s.name, taps=dict(n=len(tm), min=r3(min(tm)), max=r3(max(tm)), skew=r3(max(tm) - min(tm))) if tm else None,
                        crossings=dict(n=len(xc), min=r3(min(xc)), max=r3(max(xc)), spread=r3(max(xc) - min(xc)))))
    ok = [r for r in res if "error" not in r]
    summ = dict(window=meta["window"], ring_um=meta["ring_um"], corner=meta["corner"], ndr=meta["ndr"], sigma=meta["sigma"],
                samples=len(ok), errors=len(res) - len(ok), deck0=meta["decks"][0])
    if ok:
        nom = [r for r in ok if r["sample"] == "s000"]
        mc = [r for r in ok if r["sample"] != "s000"]
        summ["nominal"] = nom[0] if nom else None
        if mc:
            sp = [r["crossings"]["spread"] for r in mc]
            summ["mc_crossing_spread_ps"] = dict(worst=r3(max(sp)), mean=r3(sum(sp) / len(sp)),
                                                 sd=r3((sum((x - sum(sp) / len(sp)) ** 2 for x in sp) / max(1, len(sp) - 1)) ** 0.5))
            tk = [r["taps"]["skew"] for r in mc if r["taps"]]
            if tk:
                summ["mc_tap_skew_ps"] = dict(worst=r3(max(tk)), mean=r3(sum(tk) / len(tk)))
    (d / "mc_result.json").write_text(json.dumps(dict(summary=summ, samples=res), indent=1))
    print(json.dumps(summ, indent=1))
    return 0


# ------------------------------------------------------------------------------------------------ linear solve
def solve_netlist(N, corner, thev, dt=0.5, t_extra=500.0):
    """backward-Euler transient of the linear mesh; drivers = ramp (50 % at arr + d_int, 0-100 % in tr) behind R_th."""
    import numpy as np
    import scipy.sparse as sp
    import scipy.sparse.linalg as spl
    names = {}
    for a_, b_, _ in N["R"]:
        for x in (a_, b_):
            names.setdefault(x, len(names))
    for d in N["drv"]:
        names.setdefault(d["node"], len(names))
    n = len(names)
    rows, cols, vals = [], [], []
    for a_, b_, r in N["R"]:
        i, j, g = names[a_], names[b_], 1.0 / max(r, 1e-6)
        rows += [i, j, i, j]
        cols += [i, j, j, i]
        vals += [g, g, -g, -g]
    Cv = np.zeros(n)
    for k, v in N["C"].items():
        if k in names:
            Cv[names[k]] += v * 1e-15
    th = thev[corner]
    rth = th["R_ohm"] / max(1, th.get("mult", 1)) + 51.2
    gd = np.zeros(n)
    dn = np.array([names[d["node"]] for d in N["drv"]])
    np.add.at(gd, dn, 1.0 / rth)
    G = sp.csc_matrix((vals, (rows, cols)), shape=(n, n)) + sp.diags(gd)
    dts = dt * 1e-12
    A = (G + sp.diags(Cv / dts)).tocsc()
    lu = spl.splu(A)
    t0 = min(d["arr"] for d in N["drv"])
    t50 = np.array([d["arr"] - t0 + th["d_int_ps"] + th.get("dvt_ps_per_mV", 0.0) * 1e3 * (sum(d["dvn"]) + sum(d["dvp"])) / (2 * len(d["dvn"]))
                    for d in N["drv"]])
    tr = th["tr_ps"]
    vdd = VDD[corner]
    T = t50.max() + tr + t_extra
    meas = {("x", k): names[v] for k, v in N["xnodes"].items() if v in names}
    for t in N["taps"]:
        if t["inside"] and t["node"] in names:
            meas[("t", t["part"])] = names[t["node"]]
    mk = list(meas.keys())
    mi = np.array([meas[k] for k in mk])
    v = np.zeros(n)
    cross = np.full(len(mk), np.nan)
    t = 0.0
    prev = np.zeros(len(mk))
    while t < T:
        t += dt
        vs = np.clip((t - (t50 - tr / 2)) / tr, 0.0, 1.0) * vdd
        rhs = Cv / dts * v
        np.add.at(rhs, dn, vs / rth)
        v = lu.solve(rhs)
        cur = v[mi]
        hit = np.isnan(cross) & (cur >= vdd / 2) & (prev < vdd / 2)
        if hit.any():
            f = (vdd / 2 - prev[hit]) / np.maximum(cur[hit] - prev[hit], 1e-12)
            cross[hit] = t - dt + f * dt
        prev = cur
        if not np.isnan(cross).any():
            break
    res = {k: float(c) for k, c in zip(mk, cross)}
    return res, t0


def cmd_solve(a):
    rec = json.loads(Path(a.r2).read_text())
    thev = json.loads(Path(a.thev).read_text())
    box = [float(v) for v in a.window.split(",")] if a.window else None
    sigma = json.loads(a.sigma)
    out = dict(r2=a.r2, corner=a.corner, window=box, ring_um=a.ring, ndr=a.ndr or rec["ndr"], thev=thev[a.corner],
               sigma=sigma, samples=[], checked="UNCHECKED")
    for s in range(a.samples + 1):
        N = netlist(rec, a.corner, box, a.ring, sigma=sigma, seed=s, ndr=a.ndr, drv_mult=1)
        res, t0 = solve_netlist(N, a.corner, thev)
        xc = {k[1]: v for k, v in res.items() if k[0] == "x"}
        tp = {k[1]: v for k, v in res.items() if k[0] == "t"}
        row = dict(sample=s, nodes=N["nodes"], drivers=len(N["drv"]), crossings=len(xc),
                   crossing_spread_ps=r3(max(xc.values()) - min(xc.values())),
                   tap_skew_ps=r3(max(tp.values()) - min(tp.values())) if tp else None,
                   tap_arr_ps={k: r3(v) for k, v in tp.items()})
        if s == 0:
            xa = sorted(xc.items())
            row["crossing_arr_ps"] = [[r3(k[0]), r3(k[1]), r3(v)] for k, v in xa]
        out["samples"].append(row)
        print(json.dumps({k: row[k] for k in ("sample", "nodes", "drivers", "crossings", "crossing_spread_ps", "tap_skew_ps")}), flush=True)
    mc = [r for r in out["samples"] if r["sample"] > 0]
    if mc:
        out["mc_worst_crossing_spread_ps"] = max(r["crossing_spread_ps"] for r in mc)
        out["mc_worst_tap_skew_ps"] = max(r["tap_skew_ps"] for r in mc if r["tap_skew_ps"] is not None)
        # worst related-pair skew through the mesh (seam pairs, both taps)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1))
    return 0


def cmd_compare(a):
    """fit Thevenin (R_th, tr, d_int) of the linear model to an ngspice nominal window log (same deck geometry)."""
    rec = json.loads(Path(a.r2).read_text())
    meta = json.loads((Path(a.dir) / "meta.json").read_text())
    box = meta["window"]
    v = parse_log(Path(a.dir) / "s000" / "sim.log")
    N = netlist(rec, meta["corner"], box, meta["ring_um"], seed=0, ndr=meta["ndr"])
    sx = {}
    for (x, y), nn in N["xnodes"].items():
        k = f"x_{x:.2f}_{y:.2f}".replace(".", "p", 0)
        if k in v:
            sx[(x, y)] = v[k]
    best = None
    grid = json.loads(a.grid)
    for R in grid["R"]:
        for tr in grid["tr"]:
            th = {meta["corner"]: dict(R_ohm=R, tr_ps=tr, d_int_ps=0.0)}
            res, t0 = solve_netlist(N, meta["corner"], th)
            # ngspice times are from ref 50 % (=125 ps); linear from t0 at 0 -> relative
            diffs = [sx[k] - (res[("x", k)] ) for k in sx if ("x", k) in res]
            mu = sum(diffs) / len(diffs)
            err = max(abs(d - mu) for d in diffs)
            if best is None or err < best[0]:
                best = (err, R, tr, mu)
    err, R, tr, mu = best
    out = {meta["corner"]: dict(R_ohm=R, tr_ps=tr, d_int_ps=r3(mu), fit_max_err_ps=r3(err), fit_window=box,
                                fit_source=str(a.dir), note="d_int includes the ngspice ref offset (100 ps start, 25 ps to 50 %)")}
    print(json.dumps(out))
    if a.out:
        old = json.loads(Path(a.out).read_text()) if Path(a.out).exists() else {}
        old.update(out)
        Path(a.out).write_text(json.dumps(old, indent=1))
    return 0


# ------------------------------------------------------------------------------------------------ pairs / hold demand
def cmd_pairs(a):
    import qc_clk_mesh as Q
    import region_clock as RC
    rec = json.loads(Path(a.r2).read_text())
    P, dtp, parts, cores, psha = Q.load(a.plan, a.tree_plan)
    pairs = RC.seam_pairs(P, parts)
    skew = json.loads(a.mesh_skew)
    # --mesh-skew {"TT": "<die solve json>", ...}: per related pair, the worst |tap arrival difference| over the
    # nominal + MC samples of the whole-die solve (12.4a b: simulated mesh skew of THAT pair = uncertainty).
    solve = {c: json.loads(Path(v).read_text())["samples"] for c, v in skew.items() if isinstance(v, str)}
    pskew = lambda c, x, y: (r3(max(abs(s_["tap_arr_ps"][x] - s_["tap_arr_ps"][y]) for s_ in solve[c])) if c in solve else skew[c])
    aocv = json.loads(Path(a.aocv).read_text())["clock_aocv"] if a.aocv else None
    tap = {t["part"]: t for t in rec["taps"]}
    STAGE, REP_UM, DER, CORE = RC.STAGE, RC.REP_UM, RC.DERATE, RC.CORE_LAT
    fc = {c: STAGE[c][0] / (STAGE[c][0] + STAGE[c][1] * REP_UM) for c in ("TT", "FF")}

    def pess(nc, c, ir):
        cell = fc[c] * nc
        return cell * (DER["cell_late"] + (DER["ir_late"] if ir else 0.0) + DER["cell_early"]) + (nc - cell) * (DER["net_late"] + DER["net_early"])
    rows, demand = [], {}
    for x, y, edge in pairs:
        if x not in tap or y not in tap:
            continue
        r = dict(a=x, b=y, edge_um=edge, common="continuous_mesh (signed-mesh common point, 12.4a b exception)")
        for c in ("TT", "FF"):
            nc = max(RC.stage_delay(tap[x]["stub_um"], 1, c), RC.stage_delay(tap[y]["stub_um"], 1, c)) + CORE[c]
            r[c] = dict(noncommon_ps=r3(nc), flat_ps=r3(pess(nc, c, True)), flat_b1_droop_ps=r3(pess(nc, c, False)),
                        mesh_uncertainty_ps=pskew(c, x, y), total_flat_ps=r3(pess(nc, c, True) + pskew(c, x, y)),
                        total_b1_ps=r3(pess(nc, c, False) + pskew(c, x, y)))
        if aocv:
            # CLK-AOCV DRAFT (claude/clk-aocv-1026@b0c11ff91e, not a gate): k sigma_N per independent branch below the
            # common mesh, sigma_N^2 = a N + b N^2 (class A), N = tap stub stages + 10 core stages; branches independent.
            for c in ("TT", "FF"):
                f = aocv["classes"]["A"][c]["path_fit"]
                sg = lambda n: math.sqrt(max(0.0, f["a_ps2_per_stage"] * n + f["b_ps2_per_stage2"] * n * n))
                na, nb = (max(1, math.ceil(tap[q]["stub_um"] / 450.0 - 1e-9)) + 10 for q in (x, y))
                ao = aocv["k_sigma"] * math.sqrt(sg(na) ** 2 + sg(nb) ** 2)
                r[c].update(aocv_ps=r3(ao), total_aocv_ps=r3(ao + r[c]["mesh_uncertainty_ps"]))
            r["aocv"] = "DRAFT clk_aocv_table.json class A (not a gate)"
        else:
            r["aocv"] = "NOT POSTED"
        rows.append(r)
        demand["|".join(sorted((x, y)))] = math.ceil(r["FF"]["total_b1_ps"] * 10) / 10.0
    def mx(key, c):
        return r3(max(r[c][key] for r in rows))
    summ = dict(pairs=len(rows), mesh_skew_source=skew,
                **{c: dict(mesh_uncertainty_max=mx("mesh_uncertainty_ps", c), noncommon_max=mx("noncommon_ps", c), flat_max=mx("flat_ps", c), flat_b1_max=mx("flat_b1_droop_ps", c),
                           total_flat_max=mx("total_flat_ps", c), total_b1_max=mx("total_b1_ps", c),
                           **({"aocv_max": mx("aocv_ps", c), "total_aocv_max": mx("total_aocv_ps", c)} if aocv else {})) for c in ("TT", "FF")})
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "pairs_v2.json").write_text(json.dumps(dict(summary=summ, rows=rows, checked="UNCHECKED"), indent=1))
    frag = dict(clock=dict(io_hold="plan_demand", hold_demand=dict(
        source="plan", schema="opentallas.hold_demand.v1", basis="QC-CLK-MESH-2 r2 continuous signed-mesh: FF early/late CPPR-left OCV below the mesh "
        "(flat die_ci_margins cells/nets, 12.4a b1 shared droop -> IR 0 within one mesh) + signed mesh skew uncertainty; "
        "AOCV table not posted; UNCHECKED", pairs=demand, landed=[], default_ps=max(demand.values()))))
    (out / "hold_demand_fragment.json").write_text(json.dumps(frag, indent=1))
    print(json.dumps(summ, indent=1))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("plan")
    p.add_argument("--tree-plan", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--array-type", default="qfd_tile_nk_a0c", help="core array whose vertical channels carry the driver columns")
    p.add_argument("--keepout-x", type=float, default=1564.0, help="W PHY/IO column mesh+driver keep-out (GEOM-REVIEW-7 c)")
    p.add_argument("--rows", default="64", help="driver rows (uniform over the die height; cores only interrupt x)")
    p.add_argument("--gap-dy", type=float, default=432.0, help="rows = gap + j*dy, j=-m..m (rows=gaps)")
    p.add_argument("--gap-m", type=int, default=1)
    p.add_argument("--tap-at-driver", action="store_true")
    p.add_argument("--kx", type=int, default=3, help="M9 straps per driver column pitch")
    p.add_argument("--ky", type=int, default=2, help="M8 straps per driver row pitch")
    p.add_argument("--ndr", default="8w", choices=sorted(NDR))
    p.add_argument("--slide-max", type=float, default=216.0)
    p.add_argument("--stage", default=None, help='{"TT":[d0,k],"FF":[d0,k]} per-stage model override')
    p.add_argument("--no-render", action="store_true")
    p.set_defaults(fn=cmd_plan)
    d = sub.add_parser("deck")
    d.add_argument("r2")
    d.add_argument("--window", required=True, help="x0,y0,x1,y1 um (measured)")
    d.add_argument("--ring", type=float, default=1000.0, help="guard ring of neighbour straps + drivers (um)")
    d.add_argument("--corner", default="TT")
    d.add_argument("--samples", type=int, default=0)
    d.add_argument("--sigma", default='{"vt_mV": 10.0, "wire_rel": 0.05, "tree_ps_per_stage": 2.0}')
    d.add_argument("--ndr", default=None)
    d.add_argument("--drv-mult", type=int, default=1)
    d.add_argument("--rc", default="r6", choices=["r6", "plan"])
    d.add_argument("--out", required=True)
    d.set_defaults(fn=cmd_deck)
    q = sub.add_parser("parse")
    q.add_argument("dir")
    q.set_defaults(fn=cmd_parse)
    s = sub.add_parser("solve")
    s.add_argument("r2")
    s.add_argument("--thev", required=True)
    s.add_argument("--corner", default="TT")
    s.add_argument("--window", default=None)
    s.add_argument("--ring", type=float, default=0.0)
    s.add_argument("--samples", type=int, default=0)
    s.add_argument("--sigma", default='{"vt_mV": 10.0, "wire_rel": 0.05, "tree_ps_per_stage": 2.0}')
    s.add_argument("--ndr", default=None)
    s.add_argument("--rc", default="r6", choices=["r6", "plan"])
    s.add_argument("--out", required=True)
    s.set_defaults(fn=cmd_solve)
    c = sub.add_parser("compare")
    c.add_argument("r2")
    c.add_argument("dir")
    c.add_argument("--grid", default='{"R": [100, 150, 200, 250, 300, 400], "tr": [20, 30, 40, 60, 80]}')
    c.add_argument("--out", default=None)
    c.set_defaults(fn=cmd_compare)
    r = sub.add_parser("pairs")
    r.add_argument("r2")
    r.add_argument("--plan", required=True)
    r.add_argument("--tree-plan", required=True)
    r.add_argument("--mesh-skew", required=True)
    r.add_argument("--aocv", default=None)
    r.add_argument("--out", required=True)
    r.set_defaults(fn=cmd_pairs)
    a = ap.parse_args(argv)
    RC_MODE["mode"] = getattr(a, "rc", "r6")
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
