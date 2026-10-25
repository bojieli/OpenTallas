"""HBM-ARCH clock (OWNER decision via COORD 10-23: industry multi-source CTS).

Structured symmetric H-tree on M8 (H) / M9 (V), NDR 2W2S + VSS shields (NDR_TRACKS per wire), from the seam root to
a uniform grid of tap drivers (multi-source CTS: each driver feeds the partition clock taps of its cell by a short
local tree).  Topology:
  trunk  -- balanced binary tree ALONG THE SEAM (M9) from the root at the die centre to NRIB rib nodes;
  ribs   -- at every rib node one W and one E rib (M8), mirror images, each a balanced H-tree over its tile band,
            ending in NX x NY leaf drivers per side.
Seam neighbours (NW_x | NE_x at the same height) hang off the SAME rib node: their common path (removed by CPPR) is the
whole trunk; W and E ribs are mirror-identical, so related-pair skew comes only from rib OCV.  Hard cores (SM, PHY)
take their leaf with a latency offset = common latency - the core's own clock insertion (from its lib), so their pin
flops land on the common latency.

    segs, leaves, reserve = build(Wd, Hd, rects)
reserve[(part, 'H'|'V')] = M8 / M9 tracks the spine takes inside that partition (NDR_TRACKS per crossing wire)."""
NDR_TRACKS = 5          # 2W2S wire + shield each side, in routing tracks
NRIB = 4                # rib node pairs along the seam
NX, NY = 8, 4           # leaf drivers per side per rib band: x columns over the tile, y rows over the band


def build(Wd, Hd, rects):
    segs = []           # (x0, y0, x1, y1, level, layer)
    leaves = []

    def seg(a, b, lev):
        (x0, y0), (x1, y1) = a, b
        segs.append((round(x0, 3), round(y0, 3), round(x1, 3), round(y1, 3), lev, 'M9' if x0 == x1 else 'M8'))

    xc = Wd / 2.0
    # trunk: balanced binary tree along the seam over y to NRIB rib nodes at Hd/NRIB * (j + 0.5)
    def trunk(y, half, lev, n):
        if n == 1:
            return [y]
        out = []
        for s in (-1, 1):
            y2 = y + s * half / 2.0
            seg((xc, y), (xc, y2), lev)
            out += trunk(y2, half / 2.0, lev + 1, n // 2)
        return out
    ribs = trunk(Hd / 2.0, Hd / 2.0, 1, NRIB)
    lev0 = 1 + (NRIB.bit_length() - 1)

    def htree(cx, cy, w, h, nx, ny, lev):
        """balanced H-tree over the w x h cell centred at (cx, cy) to nx x ny leaves (split the longer leaf count)."""
        if nx == 1 and ny == 1:
            leaves.append((round(cx, 3), round(cy, 3)))
            return
        if nx >= ny and nx > 1:
            for s in (-1, 1):
                x2 = cx + s * w / 4.0
                seg((cx, cy), (x2, cy), lev)
                htree(x2, cy, w / 2.0, h, nx // 2, ny, lev + 1)
        else:
            for s in (-1, 1):
                y2 = cy + s * h / 4.0
                seg((cx, cy), (cx, y2), lev)
                htree(cx, y2, w, h / 2.0, nx, ny // 2, lev + 1)
    bh = Hd / NRIB
    for y in ribs:
        for side in (-1, 1):
            tx = xc + side * Wd / 4.0          # tile (half-die) centre
            seg((xc, y), (tx, y), lev0)
            htree(tx, y, Wd / 2.0, bh, NX, NY, lev0 + 1)
    # per-partition reservation: every wire crossing (or running inside) a partition takes NDR_TRACKS on its layer
    reserve = {}
    for (x0, y0, x1, y1, lev, ln) in segs:
        a0, a1 = sorted((x0, x1)); b0, b1 = sorted((y0, y1))
        for n, (rx0, ry0, rx1, ry1) in rects.items():
            if ln == 'M8' and ry0 <= b0 < ry1 and a0 < rx1 and a1 > rx0:
                reserve[(n, 'H')] = reserve.get((n, 'H'), 0) + NDR_TRACKS
            if ln == 'M9' and rx0 <= a0 < rx1 and b0 < ry1 and b1 > ry0:
                reserve[(n, 'V')] = reserve.get((n, 'V'), 0) + NDR_TRACKS
    return segs, leaves, reserve


def render(plan, segs, leaves, out_png, title):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    W, H = plan['die']['outline_um']
    fig, ax = plt.subplots(figsize=(16, 16 * H / W + 0.6))
    types = plan['partition_types']
    for p in plan['partitions']:
        w, h = types[p['type']]['outline_um']
        x, y = p['origin_um']
        hard = types[p['type']].get('hard')
        ax.add_patch(Rectangle((x, y), w, h, fill=True, fc='#d9d9d9' if hard else '#f4f4f4', ec='#888', lw=0.6))
        ax.text(x + w / 2, y + h / 2, p['name'], ha='center', va='center', fontsize=5, color='#555')
    for io in plan['die'].get('io', []):
        x0, y0, x1, y1 = io['rect_um']
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, ec='m', hatch='//', lw=0.8))
    maxl = max(s[4] for s in segs)
    for (x0, y0, x1, y1, lev, ln) in segs:
        lw = 3.2 - 2.4 * (lev - 1) / max(maxl - 1, 1)
        ax.plot([x0, x1], [y0, y1], color='#c0392b' if ln == 'M8' else '#1f5fbf', lw=lw, solid_capstyle='butt')
    ax.scatter([l[0] for l in leaves], [l[1] for l in leaves], s=10, c='k', zorder=5, label='tap driver (multi-source)')
    ax.plot([W / 2], [H / 2], marker='*', ms=18, c='gold', mec='k', zorder=6, label='seam root')
    ax.plot([], [], color='#c0392b', lw=2, label='M8 branch (NDR 2W2S + shields)')
    ax.plot([], [], color='#1f5fbf', lw=2, label='M9 branch / seam trunk')
    ax.set_xlim(-200, W + 200); ax.set_ylim(-200, H + 200); ax.set_aspect('equal')
    ax.legend(loc='upper right', fontsize=7, framealpha=0.9)
    ax.set_title(title, fontsize=10)
    fig.savefig(out_png, dpi=130, bbox_inches='tight')
    plt.close(fig)


# ------------------------------------------------------------------------------------------------------------------
# B2m (HBM 10-24): TRUE balanced binary H-tree (replaces the B2l seam-trunk fishbone for B2m and later).
# B2l findings (TRIAL-HBM 10-24): ribs hung off the seam trunk at different trunk distances, 67/256 leaves idle over
# SM / mc, 2045 partition taps on 980 leaves with leaf->tap up to 1328 um, abutted pairs diverging at level 0-1,
# insertion 4.0-5.8 ns.  Here: one root at the die centre, splits alternate H (M8) / V (M9) so every root->leaf path
# has the same length and the same layer sequence; NXL x NYL leaf cells (64 x 32 on B2: 439 x 573 um, every point of a
# cell <= 362 um from its centre); leaves without a partition tap in their cell are pruned with their empty subtrees
# (the kept wire lengths stay equal); a leaf driver that would sit on a hard partition (q_sm, PHY_N), a die.io window or
# a hard core is moved to the nearest legal 8.64-um lattice point (moved_um = the extra last-mile wire the tree
# builder pads on every leaf).  The root driver sits in the nearest legal gap of the root cell; its stub to the
# geometric centre is common to every sink (no skew).
NXL, NYL = 64, 64


def build_balanced(Wd, Hd, rects, forbid, taps, nxl=NXL, nyl=NYL, step=8.64):
    """segs [(x0,y0,x1,y1,level,layer)] in DFS order (start = the parent node at level-1), leaves [dict], reserve,
    root_driver.  forbid: [(x0,y0,x1,y1)] no-driver rects; taps: [(part, name, x, y)] die frame."""
    import math
    cw, ch = Wd / nxl, Hd / nyl
    live = {}
    for (pn, tn_, x, y) in taps:
        i, j = min(nxl - 1, max(0, int(x // cw))), min(nyl - 1, max(0, int(y // ch)))
        live.setdefault((i, j), []).append((pn, tn_, x, y))
    segs, leaves = [], []

    def bad(x, y, m=1.0):
        return any(r[0] - m < x < r[2] + m and r[1] - m < y < r[3] + m for r in forbid)

    def legal(cx, cy):
        if not bad(cx, cy):
            return cx, cy, 0.0
        best = None
        for r in range(1, 400):
            d = r * step
            for k in range(-r, r + 1):
                for (x, y) in ((cx + k * step, cy - d), (cx + k * step, cy + d), (cx - d, cy + k * step), (cx + d, cy + k * step)):
                    if 0 < x < Wd and 0 < y < Hd and not bad(x, y):
                        m = abs(x - cx) + abs(y - cy)
                        if best is None or m < best[2]:
                            best = (x, y, m)
            if best is not None and best[2] <= d:
                return round(best[0], 3), round(best[1], 3), round(best[2], 3)
        raise ValueError(f"no legal driver site near {cx, cy}")

    def any_live(i0, i1, j0, j1):
        return any(i0 <= i < i1 and j0 <= j < j1 for (i, j) in live)

    def rec(cx, cy, i0, i1, j0, j1, lev):
        ni, nj = i1 - i0, j1 - j0
        if ni == 1 and nj == 1:
            x, y, mv = legal(cx, cy)
            tp = live[(i0, j0)]
            far = max(abs(t[2] - x) + abs(t[3] - y) for t in tp)
            leaves.append(dict(xy=[round(cx, 3), round(cy, 3)], driver_um=[x, y], moved_um=mv, cell=[i0, j0],
                               taps=len(tp), tap_max_um=round(far, 1), parts=sorted({t[0] for t in tp})))
            return
        # split the axis with more cells (ties: x first) -> alternating H / V on a 2:1 grid
        if ni >= nj and ni > 1:
            h = ni // 2
            for (a0, a1, s) in ((i0, i0 + h, -1), (i0 + h, i1, 1)):
                if any_live(a0, a1, j0, j1):
                    x2 = cx + s * (ni * cw) / 4.0
                    segs.append((round(cx, 3), round(cy, 3), round(x2, 3), round(cy, 3), lev, 'M8'))
                    rec(x2, cy, a0, a1, j0, j1, lev + 1)
        else:
            h = nj // 2
            for (b0, b1, s) in ((j0, j0 + h, -1), (j0 + h, j1, 1)):
                if any_live(i0, i1, b0, b1):
                    y2 = cy + s * (nj * ch) / 4.0
                    segs.append((round(cx, 3), round(cy, 3), round(cx, 3), round(y2, 3), lev, 'M9'))
                    rec(cx, y2, i0, i1, b0, b1, lev + 1)
    rec(Wd / 2.0, Hd / 2.0, 0, nxl, 0, nyl, 1)
    rdx, rdy, rmv = legal(Wd / 2.0, Hd / 2.0)
    reserve = {}
    for (x0, y0, x1, y1, lev, ln) in segs:
        a0, a1 = sorted((x0, x1)); b0, b1 = sorted((y0, y1))
        for n, (rx0, ry0, rx1, ry1) in rects.items():
            if ln == 'M8' and ry0 <= b0 < ry1 and a0 < rx1 and a1 > rx0:
                reserve[(n, 'H')] = reserve.get((n, 'H'), 0) + NDR_TRACKS
            if ln == 'M9' and rx0 <= a0 < rx1 and b0 < ry1 and b1 > ry0:
                reserve[(n, 'V')] = reserve.get((n, 'V'), 0) + NDR_TRACKS
    return segs, leaves, reserve, dict(xy=[rdx, rdy], stub_um=rmv)


def render_balanced(plan, segs, leaves, root_driver, forbid, out_png, title):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    W, H = plan['die']['outline_um']
    fig, ax = plt.subplots(figsize=(18, 18 * H / W + 0.6))
    types = plan['partition_types']
    for p in plan['partitions']:
        w, h = types[p['type']]['outline_um']
        x, y = p['origin_um']
        hard = types[p['type']].get('hard')
        ax.add_patch(Rectangle((x, y), w, h, fill=True, fc='#cfcfcf' if hard else '#f6f6f6', ec='#777', lw=0.6))
        ax.text(x + w / 2, y + h / 2, p['name'], ha='center', va='center', fontsize=5, color='#555')
    for r in forbid:
        ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fill=False, ec='#e67e22', lw=0.3))
    for io in plan['die'].get('io', []):
        x0, y0, x1, y1 = io['rect_um']
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, ec='m', hatch='//', lw=0.8))
    maxl = max(s[4] for s in segs)
    for (x0, y0, x1, y1, lev, ln) in segs:
        lw = 3.4 - 3.0 * (lev - 1) / max(maxl - 1, 1)
        ax.plot([x0, x1], [y0, y1], color='#c0392b' if ln == 'M8' else '#1f5fbf', lw=lw, solid_capstyle='butt')
    for l in leaves:
        c = 'k' if l['moved_um'] == 0 else '#d35400'
        ax.plot([l['xy'][0], l['driver_um'][0]], [l['xy'][1], l['driver_um'][1]], color='#d35400', lw=0.6)
        ax.scatter([l['driver_um'][0]], [l['driver_um'][1]], s=5, c=c, zorder=5)
    ax.plot([W / 2], [H / 2], marker='*', ms=16, c='gold', mec='k', zorder=6, label='H-tree centre')
    ax.plot([root_driver['xy'][0]], [root_driver['xy'][1]], marker='D', ms=7, c='lime', mec='k', zorder=7,
            label='root driver (legal gap)')
    ax.scatter([], [], s=6, c='k', label='leaf driver at cell centre')
    ax.scatter([], [], s=6, c='#d35400', label='leaf driver moved off hard tile / core / io')
    ax.plot([], [], color='#c0392b', lw=2, label='M8 branch (NDR)')
    ax.plot([], [], color='#1f5fbf', lw=2, label='M9 branch (NDR)')
    ax.set_xlim(-200, W + 200); ax.set_ylim(-200, H + 200); ax.set_aspect('equal')
    ax.legend(loc='upper right', fontsize=7, framealpha=0.9)
    ax.set_title(title, fontsize=10)
    fig.savefig(out_png, dpi=140, bbox_inches='tight')
    plt.close(fig)


# ------------------------------------------------------------------------------------------------------------------
# B2m v2 (HBM 10-24): PARTITION-AWARE ZERO-SKEW TREE (topology by guillotine bisection, embedding by linear-delay
# zero-skew merge = DME on a repeated-wire model).  Why: the geometric H-tree's top cuts run THROUGH partitions
# (x = W/2 splits root and every vsN, y = H/2 splits the hub rows), so flop pairs inside one partition diverge at the
# die root (non-common path ~46 mm of wire): the worst case for OCV with CPPR (BRIEFING decision 5f: seam neighbours on
# the same spine branch).  Here every cut is chosen among straight lines across the current region that split as few
# partitions (weighted by their taps) and as little abutted seam as possible, near the tap median; each subtree is
# merged at the point that equalises both children's repeated-wire delay (ps = um * ps_per_mm / 1000), snaking the
# shorter child when the merge falls outside the segment, and merge points that land on a hard core / hard tile / io
# window are slid to the nearest legal point (the extra length is snaked on the other child).  Early core taps enter
# with a delay credit = their early_ps (core-latency contract, decision 5e), so they are delivered early by exactly that.
PS_PER_MM = 100.0


def _man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _on_l(a, b, s):
    """point at Manhattan distance s from a along the x-first L path a -> b."""
    dx = b[0] - a[0]
    if s <= abs(dx):
        return (a[0] + (s if dx >= 0 else -s), a[1])
    s2 = s - abs(dx)
    dy = b[1] - a[1]
    return (b[0], a[1] + (s2 if dy >= 0 else -s2))


def build_zst(taps, rects, forbid, seam_len, die_wh, ps_per_mm=PS_PER_MM, min_frac=0.3, step=8.64):
    """taps [(part, name, x, y, credit_um)] -> (nodes, root id).  nodes[i] = dict(xy, d (um of delay below),
    kids [(child id, wire_um, snake_um)], cut, level, parts, taps).  seam_len[(a, b)] = abutted edge length (um)."""
    Wd, Hd = die_wh
    nodes = []

    def bad(x, y, m=1.0):
        return any(r[0] - m < x < r[2] + m and r[1] - m < y < r[3] + m for r in forbid)

    def legal(p):
        if not bad(*p):
            return p
        best = None
        for r in range(1, 600):
            d = r * step
            for k in range(-r, r + 1):
                for q in ((p[0] + k * step, p[1] - d), (p[0] + k * step, p[1] + d),
                          (p[0] - d, p[1] + k * step), (p[0] + d, p[1] + k * step)):
                    if 0 < q[0] < Wd and 0 < q[1] < Hd and not bad(*q):
                        if best is None or _man(q, p) < _man(best, p):
                            best = q
            if best is not None and _man(best, p) <= d:
                return (round(best[0], 3), round(best[1], 3))
        raise ValueError(p)

    def leaf(t):
        nodes.append(dict(xy=(t[2], t[3]), d=float(t[4]), kids=[], cut=None, parts=[t[0]], taps=1, name=f"{t[0]}/{t[1]}"))
        return len(nodes) - 1

    def merge(a, b, cut):
        pa, pb = nodes[a]["xy"], nodes[b]["xy"]
        da, db = nodes[a]["d"], nodes[b]["d"]
        L = _man(pa, pb)
        x = (L + db - da) / 2.0
        x = min(max(x, 0.0), L)
        m = _on_l(pa, pb, x)
        m = legal((round(m[0], 3), round(m[1], 3)))
        la, lb = _man(pa, m), _man(pb, m)
        d = max(da + la, db + lb)
        sa, sb = d - (da + la), d - (db + lb)
        nodes.append(dict(xy=m, d=d, kids=[(a, la, round(sa, 3)), (b, lb, round(sb, 3))], cut=cut,
                          parts=sorted(set(nodes[a]["parts"]) | set(nodes[b]["parts"])),
                          taps=nodes[a]["taps"] + nodes[b]["taps"]))
        return len(nodes) - 1

    def cut_cost(T, ax, pos):
        """related pairs the cut separates, as length: 2 x (cut length inside every partition it splits, the
        partition's logic pairs diverge there) + 1 x (abutted seam length whose two partitions land on opposite
        sides: their face-register pairs diverge there).  A partition is 'split' when its taps fall on both sides."""
        k = 0 if ax == "x" else 1
        side = {}
        for t in T:
            side.setdefault(t[0], [0, 0])[1 if (t[2], t[3])[k] >= pos else 0] += 1
        c = 0.0
        for p_, v in side.items():
            if v[0] and v[1]:
                r = rects[p_]
                c += 2.0 * ((r[3] - r[1]) if ax == "x" else (r[2] - r[0]))
        maj = {p_: (1 if v[1] >= v[0] else 0) for p_, v in side.items()}
        for (pa_, pb_), ln in seam_len.items():
            if pa_ < pb_ and pa_ in maj and pb_ in maj and maj[pa_] != maj[pb_]:
                ra, rb = rects[pa_], rects[pb_]
                vert = abs(ra[2] - rb[0]) < 0.5 or abs(rb[2] - ra[0]) < 0.5
                if (ax == "x") == vert:
                    c += ln
        return c

    def rec(T, lev):
        if len(T) == 1:
            i = leaf(T[0])
            nodes[i]["level"] = lev
            return i
        best = None
        n = len(T)
        for ax, k in (("x", 2), ("y", 3)):
            S_ = sorted(T, key=lambda t: t[k])
            lo, hi = max(1, int(n * min_frac)), min(n - 1, n - int(n * min_frac))
            if hi < lo:
                lo, hi = n // 2, n // 2
            cands = set()
            for i in range(lo, hi + 1):
                a, b = S_[i - 1][k], S_[i][k]
                if b - a > 1e-6:
                    cands.add(round((a + b) / 2, 3))
                    # partition boundaries between a and b: prefer the exact edge (seam) if one lies there
                    for r in rects.values():
                        for e in ((r[0], r[2]) if ax == "x" else (r[1], r[3])):
                            if a < e <= b:
                                cands.add(round(e, 3))
            ext = (max(t[k] for t in T) - min(t[k] for t in T)) or 1.0
            for pos in cands:
                nl = sum(1 for t in T if t[k] < pos)
                if nl == 0 or nl == n:
                    continue
                bal = abs(nl / n - 0.5)
                c = cut_cost(T, ax, pos) * (1.0 + 2.0 * bal)
                if best is None or c < best[0]:
                    best = (c, ax, pos, k)
        if best is None:      # coincident taps: split the list
            L_, R_ = T[: n // 2], T[n // 2:]
            cut = ("list", None)
        else:
            _, ax, pos, k = best
            L_ = [t for t in T if t[k] < pos]
            R_ = [t for t in T if t[k] >= pos]
            cut = (ax, pos)
        a = rec(L_, lev + 1)
        b = rec(R_, lev + 1)
        i = merge(a, b, cut)
        nodes[i]["level"] = lev
        return i
    import sys as _s
    _s.setrecursionlimit(10000)
    root = rec([tuple(t) for t in taps], 0)
    return nodes, root


def zst_lca_report(nodes, root, ps_per_mm=PS_PER_MM):
    """for every partition: the shallowest tree node where two of its own taps diverge (non-common delay below it);
    returns {part: (level, d_um)}."""
    out = {}

    def walk(i):
        nd = nodes[i]
        if not nd["kids"]:
            return {nd["parts"][0]}
        sets = [walk(k) for k, _, _ in nd["kids"]]
        both = sets[0] & sets[1]
        for p in both:
            if p not in out or nd["level"] < out[p][0]:
                out[p] = (nd["level"], nd["d"])
        return sets[0] | sets[1]
    walk(root)
    return out


def zst_segments(nodes, root):
    """DFS segment list (x-first L per edge, corner as its own node) + leaves, in the clock_htree.json form."""
    segs = []

    def walk(i, lev):
        p = nodes[i]["xy"]
        for k, _, _ in nodes[i]["kids"]:
            q = nodes[k]["xy"]
            c = (q[0], p[1])
            l2 = lev
            if abs(c[0] - p[0]) > 1e-6:
                segs.append((p[0], p[1], c[0], c[1], l2 + 1, "M8"))
                l2 += 1
            if abs(q[1] - c[1]) > 1e-6:
                segs.append((c[0], c[1], q[0], q[1], l2 + 1, "M9"))
                l2 += 1
            walk(k, l2)
    walk(root, 0)
    return segs
