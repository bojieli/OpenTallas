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
