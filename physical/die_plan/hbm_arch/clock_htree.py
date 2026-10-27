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
import math
NDR_TRACKS = 5          # 2W2S wire + shield each side, in routing tracks
NRIB = 4                # rib node pairs along the seam
NX, NY = 8, 4           # leaf drivers per side per rib band: x columns over the tile, y rows over the band


REP_UM = 450.0          # repeater spacing on M8 / M9 (owner 10-23: 450 um)


def build(Wd, Hd, rects, hard=()):
    """-> segs, ends, reserve, stats.  ends: [{xy, kind tap|pin, part, path_um, buffers, pad_um}]."""
    nodes = [dict(xy=(Wd / 2.0, Hd / 2.0), parent=None, seg=None, kids=[])]

    def add(par, xy, lev):
        x0, y0 = nodes[par]['xy']
        ln = 'M9' if abs(x0 - xy[0]) < 1e-6 else 'M8'
        nodes.append(dict(xy=xy, parent=par, kids=[], seg=(x0, y0, xy[0], xy[1], lev, ln)))
        nodes[par]['kids'].append(len(nodes) - 1)
        return len(nodes) - 1
    xc = Wd / 2.0

    def trunk(par, half, lev, n):
        if n == 1:
            return [par]
        y = nodes[par]['xy'][1]
        out = []
        for sg in (-1, 1):
            out += trunk(add(par, (xc, y + sg * half / 2.0), lev), half / 2.0, lev + 1, n // 2)
        return out
    ribs = trunk(0, Hd / 2.0, 1, NRIB)
    lev0 = 1 + (NRIB.bit_length() - 1)

    def htree(par, w, h, nx, ny, lev):
        cx, cy = nodes[par]['xy']
        if nx == 1 and ny == 1:
            return
        if nx >= ny and nx > 1:
            for sg in (-1, 1):
                htree(add(par, (cx + sg * w / 4.0, cy), lev), w / 2.0, h, nx // 2, ny, lev + 1)
        else:
            for sg in (-1, 1):
                htree(add(par, (cx, cy + sg * h / 4.0), lev), w, h / 2.0, nx, ny // 2, lev + 1)
    bh = Hd / NRIB
    for r in ribs:
        y = nodes[r]['xy'][1]
        for side in (-1, 1):
            htree(add(r, (xc + side * Wd / 4.0, y), lev0), Wd / 2.0, bh, NX, NY, lev0 + 1)

    def inside(xy, rc):
        return rc[0] <= xy[0] <= rc[2] and rc[1] <= xy[1] <= rc[3]

    def part_of(xy):
        for n, rc in rects.items():
            if inside(xy, rc):
                return n
        return None
    leaves = [i for i, nd in enumerate(nodes) if not nd['kids']]
    # hard blocks: no tap drivers over them; ONE feed to the block's clock pin = the root of the largest subtree whose
    # leaves all lie in the block (its ETM latency is compensated on that branch)
    def sub_leaves(i):
        return [i] if not nodes[i]['kids'] else [l for k in nodes[i]['kids'] for l in sub_leaves(k)]
    keep, pins = set(), {}
    for i in range(len(nodes)):
        ls = sub_leaves(i)
        ps = {part_of(nodes[l]['xy']) for l in ls}
        if len(ps) == 1:
            p = ps.pop()
            if p in hard:
                cur = pins.get(p)
                if cur is None or len(ls) > len(sub_leaves(cur)):
                    pins[p] = i
    for l in leaves:
        if part_of(nodes[l]['xy']) not in hard:
            keep.add(l)
    keep |= set(pins.values())
    live = set()
    for k in keep:
        j = k
        while j is not None and j not in live:
            live.add(j); j = nodes[j]['parent']

    def path(i):
        L, B = 0.0, 0
        j = i
        while nodes[j]['parent'] is not None:
            x0, y0, x1, y1, _, _ = nodes[j]['seg']
            d = abs(x1 - x0) + abs(y1 - y0)
            L += d; B += max(1, math.ceil(d / REP_UM))
            j = nodes[j]['parent']
        return L, B
    Lleaf = path(leaves[0])[0]
    ends = []
    for k in sorted(keep):
        L, B = path(k)
        hp = next((p for p, i in pins.items() if i == k), None)
        ends.append(dict(xy=[round(v, 3) for v in nodes[k]['xy']], kind='pin' if hp else 'tap',
                         part=hp or part_of(nodes[k]['xy']), path_um=round(L, 1), buffers=B,
                         pad_um=round(Lleaf - L, 1) if hp else 0.0))
    segs = [tuple(round(v, 3) for v in nodes[i]['seg'][:4]) + nodes[i]['seg'][4:] for i in sorted(live) if nodes[i]['seg']]
    reserve = {}
    for (x0, y0, x1, y1, lev, ln) in segs:
        a0, a1 = sorted((x0, x1)); b0, b1 = sorted((y0, y1))
        for n, (rx0, ry0, rx1, ry1) in rects.items():
            if ln == 'M8' and ry0 <= b0 < ry1 and a0 < rx1 and a1 > rx0:
                reserve[(n, 'H')] = reserve.get((n, 'H'), 0) + NDR_TRACKS
            if ln == 'M9' and rx0 <= a0 < rx1 and b0 < ry1 and b1 > ry0:
                reserve[(n, 'V')] = reserve.get((n, 'V'), 0) + NDR_TRACKS
    taps = [e for e in ends if e['kind'] == 'tap']
    stats = dict(taps=len(taps), hard_pins=len(pins), removed_leaves=len(leaves) - len([l for l in leaves if l in keep]),
                 tap_path_um=[min(e['path_um'] for e in taps), max(e['path_um'] for e in taps)],
                 tap_buffers=[min(e['buffers'] for e in taps), max(e['buffers'] for e in taps)],
                 pin_path_um={e['part']: e['path_um'] for e in ends if e['kind'] == 'pin'},
                 pin_pad_um={e['part']: e['pad_um'] for e in ends if e['kind'] == 'pin'},
                 seam_pair_common_um=round(Hd / 4.0 + Hd / 8.0, 1), rep_um=REP_UM)
    return segs, ends, reserve, stats


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
        off = (lev - 1) * 28.0                     # parallel track groups of overlapping levels drawn side by side
        if ln == 'M8':
            ax.plot([x0, x1], [y0 + off, y1 + off], color='#c0392b', lw=lw, solid_capstyle='butt')
        else:
            ax.plot([x0 + off, x1 + off], [y0, y1], color='#1f5fbf', lw=lw, solid_capstyle='butt')
    taps = [e['xy'] for e in leaves if e['kind'] == 'tap']
    pins = [e['xy'] for e in leaves if e['kind'] == 'pin']
    ax.scatter([l[0] for l in taps], [l[1] for l in taps], s=10, c='k', zorder=5, label='tap driver (multi-source)')
    ax.scatter([l[0] for l in pins], [l[1] for l in pins], s=70, marker='s', c='lime', ec='k', zorder=6,
               label='hard-block clock pin feed (ETM latency compensated)')
    ax.plot([W / 2], [H / 2], marker='*', ms=18, c='gold', mec='k', zorder=6, label='seam root')
    ax.plot([], [], color='#c0392b', lw=2, label='M8 branch (NDR 2W2S + shields)')
    ax.plot([], [], color='#1f5fbf', lw=2, label='M9 branch / seam trunk')
    ax.set_xlim(-200, W + 200); ax.set_ylim(-200, H + 200); ax.set_aspect('equal')
    ax.legend(loc='upper right', fontsize=7, framealpha=0.9)
    ax.set_title(title, fontsize=10)
    fig.savefig(out_png, dpi=130, bbox_inches='tight')
    plt.close(fig)
