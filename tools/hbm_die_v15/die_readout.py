#!/usr/bin/env python3
"""Standard die-trial readout (coordinator/owner 10-16 07:45): for a die case dir (run.tcl + die.v + views/*.lef,
out/grt_congestion.rpt, optional out/paths_{tt_max,ff_min}.txt):
  readout_congestion.png  GRT overflow heat map (marker count per 100-um bin) + block outlines + top-20 data flows
  readout.json            hot spots (connected overflow bins) with measured overflow, the instance pairs whose nets
                          make them, a class (pin-face/density | partner placement | channel/metal margin |
                          clock/relay structure) and the indicated fix; top flows; timing failures grouped by block
                          pair (die_case_classify-style) when the STA path dumps exist.
    die_readout.py CASE_DIR [--out DIR] [--bin 100]
Classes are rule-based from geometry (stated in each hot spot's 'why'); a human still reads the PNG."""
import argparse, json, re, collections
from pathlib import Path
import numpy as np


def lef_sizes(views):
    out = {}
    for f in Path(views).glob('*.lef'):
        t = f.read_text(errors='replace')
        for m in re.finditer(r'MACRO\s+(\S+).*?SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', t, re.S):
            out[m.group(1)] = (float(m.group(2)), float(m.group(3)))
    return out


def parse_die(dv):
    inst_master, net_insts = {}, collections.defaultdict(set)
    cur = None
    for line in open(dv, errors='replace'):
        m = re.match(r'^\s{2}([A-Za-z_]\w*)\s+([A-Za-z_]\w*)\s*\($', line)
        if m:
            cur = m.group(2); inst_master[cur] = m.group(1); continue
        if cur and line.lstrip().startswith('.'):
            for n in re.findall(r'[\(\{,]\s*([A-Za-z_]\w*)', line.split('(', 1)[1] if '(' in line else ''):
                net_insts[n].add(cur)
        elif cur and line.strip().startswith(');'):
            cur = None
    return inst_master, net_insts


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('case'); ap.add_argument('--out'); ap.add_argument('--bin', type=float, default=100.0)
    a = ap.parse_args()
    case = Path(a.case); out = Path(a.out or case / 'out'); out.mkdir(parents=True, exist_ok=True)
    sizes = lef_sizes(case / 'views')
    im, nets = parse_die(case / 'die.v')
    place = {}
    for l in open(case / 'run.tcl'):
        m = re.match(r'place_inst -name (\S+) -location \{([\d.]+) ([\d.]+)\} -orientation (\S+)', l)
        if m and m.group(1) in im and im[m.group(1)] in sizes:
            w, h = sizes[im[m.group(1)]]
            if m.group(4) in ('R90', 'R270', 'MXR90', 'MYR90'):
                w, h = h, w
            place[m.group(1)] = (float(m.group(2)), float(m.group(3)), w, h)
    W = max(x + w for x, y, w, h in place.values()); H = max(y + h for x, y, w, h in place.values())
    # flows: instance pairs sharing signal nets (2..8 tiles, clock/reset excluded)
    flow = collections.Counter(); net_pair = {}
    for n, s in nets.items():
        if n.startswith(('n_dk', 'clk', 'rst')) or not (2 <= len(s) <= 8):
            continue
        s = sorted(i for i in s if i in place)
        for i in range(len(s)):
            for j in range(i + 1, len(s)):
                flow[(s[i], s[j])] += 1
        net_pair[n] = s
    # congestion markers
    rpt = case / 'out' / 'grt_congestion.rpt'
    nb = (int(H // a.bin) + 1, int(W // a.bin) + 1)
    heat = np.zeros(nb); bin_nets = collections.defaultdict(collections.Counter)
    if rpt.exists():
        srcs = []
        for line in open(rpt, errors='replace'):
            if 'srcs:' in line:
                srcs = re.findall(r'net:(\S+)', line)
            m = re.search(r'bbox = \(([\d.]+), ([\d.]+)\) - \(([\d.]+), ([\d.]+)\)', line)
            if m:
                x, y = (float(m.group(1)) + float(m.group(3))) / 2, (float(m.group(2)) + float(m.group(4))) / 2
                bi, bj = int(y // a.bin), int(x // a.bin)
                if 0 <= bi < nb[0] and 0 <= bj < nb[1]:
                    heat[bi, bj] += 1
                    for n in srcs:
                        bin_nets[(bi, bj)][re.sub(r'\[\d+\]$', '', n)] += 1
    # hot spots = connected bins with markers
    from scipy import ndimage
    lab, nl = ndimage.label(heat > 0)
    spots = []
    for k in range(1, nl + 1):
        cells = np.argwhere(lab == k); tot = float(heat[lab == k].sum())
        y0, x0 = cells.min(0) * a.bin; y1, x1 = (cells.max(0) + 1) * a.bin
        pairs = collections.Counter()
        for bi, bj in map(tuple, cells):
            for n, c in bin_nets[(bi, bj)].items():
                pr = net_pair.get(n)
                if pr and len(pr) >= 2:
                    pairs[(pr[0], pr[-1])] += c
        inside = [i for i, (x, y, w, h) in place.items() if x < x1 and x + w > x0 and y < y1 and y + h > y0]
        near_face = any(abs(x0 - (x + w)) < 2 * a.bin or abs(x1 - x) < 2 * a.bin or abs(y0 - (y + h)) < 2 * a.bin or
                        abs(y1 - y) < 2 * a.bin for x, y, w, h in (place[i] for i in inside if not i.startswith('rly_')))
        relay = sum(c for (p, q), c in pairs.items() if p.startswith('rly_') or q.startswith('rly_'))
        if relay > 0.5 * sum(pairs.values() or [1]):
            cls, fix = 'clock/relay structure', 'relay hop crosses blocks: carve feedthrough / re-space relays <= 480 um'
        elif near_face and (x1 - x0) * (y1 - y0) <= 4 * a.bin * a.bin * 4:
            cls, fix = 'pin-face/density', 'spread the face pin window / taller face'
        elif len({p.split('_')[0] for pr in pairs for p in pr}) <= 2 and pairs:
            cls, fix = 'partner placement', 'move the partners adjacent / re-face the link'
        else:
            cls, fix = 'channel/metal margin', 'widen the channel or move traffic to another layer pair'
        spots.append(dict(bbox_um=[float(x0), float(y0), float(x1), float(y1)], markers=tot, cls=cls, fix=fix,
                          top_pairs=[[p, q, c] for (p, q), c in pairs.most_common(5)]))
    spots.sort(key=lambda s: -s['markers'])
    # timing grouped by block pair
    timing = {}
    for corner in ('tt_max', 'ff_min'):
        f = case / 'out' / f'paths_{corner}.txt'
        if not f.exists():
            continue
        g = collections.defaultdict(lambda: [0, 0, 0.0, 0.0])
        for l in open(f):
            p = l.split()
            if len(p) < 3:
                continue
            s = float(p[2]); sp, ep = p[0].split('/')[0], p[1].split('/')[0]
            k = (re.sub(r'_(\w\w)\d*.*$', '', sp), re.sub(r'_(\w\w)\d*.*$', '', ep))
            r = g[k]; r[0] += 1
            if s < 0:
                r[1] += 1; r[2] = min(r[2], s); r[3] += s
        timing[corner] = sorted([dict(start=k[0], end=k[1], endpoints=v[0], failing=v[1], wns_ps=round(v[2], 1),
                                      tns_ps=round(v[3], 1)) for k, v in g.items()], key=lambda d: d['tns_ps'])
    # end-to-end flows: contract relay chains (instances named rly_* / *_rly* / stn) into the blocks they connect
    isr = lambda i: i.startswith('rly_') or '_rly' in i or i.startswith('stn')
    par = {}

    def fd(x):
        while par.get(x, x) != x:
            x = par[x]
        return x
    for (p, q), c in flow.items():
        if isr(p) and isr(q):
            par[fd(p)] = fd(q)
    ends = collections.defaultdict(lambda: collections.Counter())
    e2e = collections.Counter()
    for (p, q), c in flow.items():
        if isr(p) != isr(q):
            r, b = (p, q) if isr(p) else (q, p)
            ends[fd(r)][b] = max(ends[fd(r)][b], c)
        elif not isr(p):
            e2e[(p, q)] += c
    for comp, bs in ends.items():
        bl = sorted(bs)
        for i in range(len(bl)):
            for j in range(i + 1, len(bl)):
                e2e[(bl[i], bl[j])] += min(bs[bl[i]], bs[bl[j]])
    top = e2e.most_common(20)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(16, 16 * H / W))
    if heat.any():
        ax.imshow(np.ma.masked_equal(heat, 0), origin='lower', extent=[0, nb[1] * a.bin, 0, nb[0] * a.bin], cmap='hot_r', alpha=0.85)
    for i, (x, y, w, h) in place.items():
        if i.startswith('rly_'):
            ax.add_patch(plt.Rectangle((x, y), w, h, fill=True, color='0.6', lw=0))
        else:
            ax.add_patch(plt.Rectangle((x, y), w, h, fill=False, ec='steelblue', lw=0.6))
    mx = top[0][1] if top else 1
    for (p, q), c in top:
        (xa, ya, wa, ha), (xb, yb, wb, hb) = place[p], place[q]
        ax.plot([xa + wa / 2, xb + wb / 2], [ya + ha / 2, yb + hb / 2], color='tab:green', lw=0.5 + 3 * c / mx, alpha=0.7)
    for k, s in enumerate(spots[:15]):
        x0, y0, x1, y1 = s['bbox_um']
        ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, ec='purple', lw=1.2))
        ax.text(x1, y1, f"H{k+1} {s['cls'].split('/')[0]}", fontsize=7, color='purple')
    ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect('equal')
    ax.set_title(f"{case.name}: GRT overflow markers / {a.bin:.0f} um bin, block outlines, top-20 flows (green), hot spots (purple)")
    fig.savefig(out / 'readout_congestion.png', dpi=110, bbox_inches='tight')
    rec = dict(case=str(case), die_um=[W, H], markers=float(heat.sum()), hot_spots=spots[:30],
               top_flows=[[p, q, c] for (p, q), c in top], timing_by_block_pair=timing,
               png=str(out / 'readout_congestion.png'))
    (out / 'readout.json').write_text(json.dumps(rec, indent=1))
    print(json.dumps(dict(markers=rec['markers'], hot_spots=len(spots), png=rec['png'],
                          top3=[(s['cls'], s['markers'], s['bbox_um']) for s in spots[:3]])))


if __name__ == '__main__':
    main()
