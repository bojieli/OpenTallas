#!/usr/bin/env python3
"""Qwen compute die trial: standard readout (coordinator / owner 2026-10-16).

  (1) die_readout_congestion.png  GRT congestion heat map + block outlines + the top-N data flows (bits x Manhattan mm)
  (2) hotspots.json / .txt        every hot spot (merged hot gcells) with measured numbers and a cause class:
                                    pin-face/density | partner placement | channel/metal margin | clock/relay structure
  (3) timing_groups.json / .txt   failing endpoints grouped by (launch block, capture block) family pair and cause

    python3 tools/qwen_split/die_readout.py --model OUT/rom_tp8b.json --heatmap GRT/grt_heatmap.csv \
        [--ends STA/grt_tt_ends.rpt --summary STA/grt_tt_summary.rpt] --out DIR [--title T] [--top 20]

Inputs: rom_tp8b.json (the GEN's insts n/m/x/y/w/h and buses [name, class, bits, [[inst, port], ...]]),
grt_heatmap.csv (gui::dump_heatmap Routing, written by tools/qwen_kv_die/chain/grt.tcl step heat: x0,y0,x1,y1,value %),
OpenSTA '-format end' and '-format summary' reports.  Classification is a measured heuristic; the readout lists the
numbers it used so a reviewer can overrule it.
"""
import argparse
import collections
import csv
import json
import math
import re
from pathlib import Path

RELAY = re.compile(r'^(q[fk]d_rly|qfd_rst_rep|qfd_rlyp)')
CLOCKISH = re.compile(r'(^|_)(ck|clk)|rst|reset', re.I)


def fam(m):
    m = re.sub(r'_\d+x\d+$', '', m)
    mm = re.match(r'(qfd_rly|qfd_rst_rep|qfd_tile|qfd_xcst|qfd_xcol|qfd_port_tiles|qfd_sp_\w+?|ot_qfd_\w+?|qfd_\w+?)(_\d|_[nsewNSEW]$|$)', m)
    return mm.group(1) if mm else m


def bus_base(name):
    return re.sub(r'(__r\d+|_r\d+|__s\d+|__t\d+)+$', '', name)


def load_model(p):
    d = json.loads(Path(p).read_text())
    insts = {i['n']: i for i in d['insts']}
    return insts, d['buses']


def flows(insts, buses):
    """end-to-end flows: buses sharing a base name are merged, relays removed; source = first non-relay endpoint"""
    agg = collections.OrderedDict()
    for name, cl, bits, eps in buses:
        base = bus_base(name)
        ends = [n for n in (e if isinstance(e, str) else e[0] for e in eps) if n in insts and not RELAY.match(insts[n]['m'])]
        r = agg.setdefault(base, dict(bus=base, cls=cl, bits=0, ends=[]))
        r['bits'] = max(r['bits'], int(bits))
        for e in ends:
            if e not in r['ends']:
                r['ends'].append(e)
    out = []
    for r in agg.values():
        if len(r['ends']) < 2 or r['cls'] in ('clock_trunk',):
            continue
        c = [(insts[e]['x'] + insts[e]['w'] / 2, insts[e]['y'] + insts[e]['h'] / 2) for e in r['ends']]
        src = c[0]
        far = max(c[1:], key=lambda q: abs(q[0] - src[0]) + abs(q[1] - src[1]))
        L = (abs(far[0] - src[0]) + abs(far[1] - src[1])) / 1000.0
        out.append(dict(r, src=src, far=far, mm=round(L, 3), bit_mm=round(r['bits'] * L, 1), fanout=len(r['ends']) - 1))
    out.sort(key=lambda r: -r['bit_mm'])
    return out


def load_heat(p):
    cells = []
    with open(p) as f:
        rd = csv.reader(f)
        for row in rd:
            try:
                v = [float(x) for x in row[:4]] + [float(row[-1])]
            except (ValueError, IndexError):
                continue
            cells.append(v)
    return cells


def hotspots(cells, insts, fl, thr, top):
    hot = [c for c in cells if c[4] >= thr]
    hot.sort(key=lambda c: -c[4])
    used, spots = set(), []
    for k, c in enumerate(hot):
        if k in used:
            continue
        x0, y0, x1, y1 = c[:4]
        grp = [c]
        used.add(k)
        for j, d in enumerate(hot):        # merge hot cells within 2 cell pitches
            if j in used:
                continue
            p = 2 * max(x1 - x0, y1 - y0)
            if d[0] < x1 + p and d[2] > x0 - p and d[1] < y1 + p and d[3] > y0 - p:
                grp.append(d)
                used.add(j)
                x0, y0, x1, y1 = min(x0, d[0]), min(y0, d[1]), max(x1, d[2]), max(y1, d[3])
        spots.append(dict(rect=[round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)], peak=round(max(g[4] for g in grp), 1),
                          mean=round(sum(g[4] for g in grp) / len(grp), 1), cells=len(grp)))
        if len(spots) >= top:
            break
    big = [i for i in insts.values() if not RELAY.match(i['m'])]
    rel = [i for i in insts.values() if RELAY.match(i['m'])]
    for s in spots:
        x0, y0, x1, y1 = s['rect']
        m = 50.0
        near = [i for i in big if i['x'] < x1 + m and i['x'] + i['w'] > x0 - m and i['y'] < y1 + m and i['y'] + i['h'] > y0 - m]
        inside = [i for i in big if i['x'] <= x0 and i['x'] + i['w'] >= x1 and i['y'] <= y0 and i['y'] + i['h'] >= y1]
        nrel = sum(1 for i in rel if x0 - m < i['x'] < x1 + m and y0 - m < i['y'] < y1 + m)
        cross = []
        for f in fl:                        # L-shaped route src -> far (x first, then y) through the window
            (ax, ay), (bx, by) = f['src'], f['far']
            hit = (min(ax, bx) <= x1 and max(ax, bx) >= x0 and y0 <= ay <= y1) or (min(ay, by) <= y1 and max(ay, by) >= y0 and x0 <= bx <= x1)
            if hit:
                cross.append((f['bus'], f['cls'], f['bits'], f['mm']))
        cross.sort(key=lambda q: -q[2])
        cbits = sum(q[2] for q in cross)
        long_bits = sum(q[2] for q in cross if q[3] > 3.0)
        clk_bits = sum(q[2] for q in cross if CLOCKISH.search(q[0]) or q[1] in ('reset',))
        # cause heuristic (numbers recorded so the class can be overruled)
        if inside:
            cause = 'pin-face/density'
            why = f'hot cell inside block {inside[0]["n"]} ({inside[0]["m"]}): block-internal / over-the-block routing'
        elif nrel >= 40 or (cbits and clk_bits / cbits > 0.3):
            cause = 'clock/relay structure'
            why = f'{nrel} relay/reset repeaters within 50 um; clock/reset share {clk_bits}/{cbits} b'
        elif cbits and long_bits / cbits > 0.5:
            cause = 'partner placement'
            why = f'{long_bits}/{cbits} crossing bits belong to flows > 3 mm (partners far apart)'
        elif len(near) >= 2:
            cause = 'channel/metal margin'
            why = f'between {len(near)} blocks ({", ".join(sorted({i["m"] for i in near})[:4])}); channel capacity'
        else:
            cause = 'pin-face/density'
            why = f'next to {near[0]["n"] if near else "?"} pin face'
        s.update(cause=cause, why=why, blocks_near=sorted({f'{i["n"]}:{fam(i["m"])}' for i in near})[:12], relays_near=nrel,
                 crossing_bits=cbits, crossing_long_bits=long_bits, crossing_top=cross[:6])
    return spots


def timing_groups(ends_p, summ_p, insts):
    start = {}
    if summ_p and Path(summ_p).exists():
        for ln in Path(summ_p).read_text(errors='replace').splitlines():
            f = ln.split()
            if len(f) >= 3 and '/' in f[1] and f[-1].replace('.', '', 1).lstrip('-').replace('.', '').isdigit():
                start[f[1]] = f[0]
    grp = collections.defaultdict(lambda: dict(n=0, worst=0.0, causes=collections.Counter(), ex=None))
    tot = 0
    for ln in Path(ends_p).read_text(errors='replace').splitlines():
        if 'VIOLATED' not in ln:
            continue
        f = ln.replace('(VIOLATED)', '').split()
        try:
            sl = float(f[-1])
        except ValueError:
            continue
        ep = f[0]
        ei, epin = ep.split('/', 1) if '/' in ep else (ep, '')
        sp = start.get(ep, '?')
        si = sp.split('/', 1)[0]
        em = insts.get(ei, {}).get('m', '?')
        sm = insts.get(si, {}).get('m', '?')
        if re.search(r'rst|reset', epin):
            cause = 'reset distribution'
        elif RELAY.match(em) and RELAY.match(sm):
            cause = 'relay hop (over-reach)'
        elif RELAY.match(em) or RELAY.match(sm):
            cause = 'block<->relay boundary'
        elif si in insts and ei in insts:
            a, b = insts[si], insts[ei]
            d = abs(a['x'] + a['w'] / 2 - b['x'] - b['w'] / 2) + abs(a['y'] + a['h'] / 2 - b['y'] - b['h'] / 2)
            cause = 'unrelayed long wire' if d > 500 else 'block boundary (view/pin timing)'
        else:
            cause = 'unresolved launch'
        key = (fam(sm) if sm != '?' else '?', fam(em))
        g = grp[key]
        g['n'] += 1
        g['causes'][cause] += 1
        if sl < g['worst']:
            g['worst'], g['ex'] = sl, f'{sp} -> {ep}'
        tot += 1
    rows = [dict(launch=k[0], capture=k[1], n=v['n'], worst_ps=round(v['worst'], 1), causes=dict(v['causes'].most_common()),
                 example=v['ex']) for k, v in grp.items()]
    rows.sort(key=lambda r: r['worst_ps'])
    return tot, rows


def render(out, insts, cells, fl, spots, title, top):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    W = max(i['x'] + i['w'] for i in insts.values())
    H = max(i['y'] + i['h'] for i in insts.values())
    fig, ax = plt.subplots(figsize=(22, 22 * H / W + 1.5))
    if cells:
        import numpy as np
        xs = sorted({c[0] for c in cells})
        ys = sorted({c[1] for c in cells})
        xi = {x: k for k, x in enumerate(xs)}
        yi = {y: k for k, y in enumerate(ys)}
        g = np.zeros((len(ys), len(xs)))
        for c in cells:
            g[yi[c[1]], xi[c[0]]] = c[4]
        dx = cells[0][2] - cells[0][0]
        dy = cells[0][3] - cells[0][1]
        im = ax.imshow(g, origin='lower', extent=[xs[0], xs[-1] + dx, ys[0], ys[-1] + dy], cmap='inferno', vmin=0, vmax=100,
                       interpolation='nearest', alpha=0.9)
        fig.colorbar(im, ax=ax, fraction=0.02, pad=0.01, label='GRT routing usage %')
    for i in insts.values():
        if RELAY.match(i['m']):
            continue
        t = i['m'].startswith('qfd_tile')
        ax.add_patch(Rectangle((i['x'], i['y']), i['w'], i['h'], fill=False, lw=0.3 if t else 0.9,
                               ec='#7fd3ff' if t else '#00ff9c'))
        if not t and i['w'] * i['h'] > 4e5:
            ax.text(i['x'] + i['w'] / 2, i['y'] + i['h'] / 2, i['n'], color='#00ff9c', fontsize=7, ha='center', va='center')
    mx = max((f['bit_mm'] for f in fl[:top]), default=1)
    for k, f in enumerate(fl[:top]):
        (ax_, ay), (bx, by) = f['src'], f['far']
        ax.plot([ax_, bx, bx], [ay, ay, by], color='#3fa9ff', lw=1 + 6 * f['bit_mm'] / mx, alpha=0.75)
        ax.text(bx, by, f'{k + 1}', color='white', fontsize=8, fontweight='bold')
    for k, s in enumerate(spots):
        x0, y0, x1, y1 = s['rect']
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, lw=1.5, ec='red'))
        ax.text(x1, y1, f'H{k + 1}', color='red', fontsize=9, fontweight='bold')
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.set_aspect('equal')
    ax.set_title(title + '  |  blue L-lines: top data flows by bit x mm (numbered); red boxes: hot spots H#', fontsize=11)
    fig.savefig(out, dpi=110, bbox_inches='tight')
    plt.close(fig)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--model', required=True)
    ap.add_argument('--heatmap')
    ap.add_argument('--ends')
    ap.add_argument('--summary')
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--title', default='Qwen compute die')
    ap.add_argument('--top', type=int, default=20)
    ap.add_argument('--hot', type=float, default=85.0, help='hot cell threshold, usage %')
    ap.add_argument('--spots', type=int, default=12)
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    insts, buses = load_model(a.model)
    fl = flows(insts, buses)
    cells = load_heat(a.heatmap) if a.heatmap and Path(a.heatmap).exists() else []
    spots = hotspots(cells, insts, fl, a.hot, a.spots) if cells else []
    rec = dict(schema='qwen.compute.die_readout.v1', model=a.model, heatmap=a.heatmap, hot_threshold_pct=a.hot,
               top_flows=[{k: f[k] for k in ('bus', 'cls', 'bits', 'fanout', 'mm', 'bit_mm', 'ends')} | dict(ends=f['ends'][:6])
                          for f in fl[:a.top]],
               total_bit_mm=round(sum(f['bit_mm'] for f in fl), 1), hotspots=spots)
    lines = [f'# {a.title}: top {a.top} flows (bits x Manhattan mm), total {rec["total_bit_mm"]:,.0f} bit-mm']
    for k, f in enumerate(fl[:a.top]):
        lines.append(f'{k + 1:2d} {f["bus"]:34s} {f["cls"]:12s} {f["bits"]:6d} b x {f["mm"]:6.2f} mm = {f["bit_mm"]:9.0f}  '
                     f'{f["ends"][0]} -> {len(f["ends"]) - 1} sink(s)')
    lines.append(f'\n# hot spots (GRT usage >= {a.hot}%)' + ('' if cells else ': NO heat map given'))
    for k, s in enumerate(spots):
        lines.append(f'H{k + 1} {s["rect"]} peak {s["peak"]}% mean {s["mean"]}% cells {s["cells"]}: {s["cause"]} -- {s["why"]}; '
                     f'crossing {s["crossing_bits"]} b (long {s["crossing_long_bits"]}); near {", ".join(s["blocks_near"][:5])}')
    if a.ends:
        tot, rows = timing_groups(a.ends, a.summary, insts)
        rec['timing'] = dict(violating_endpoints=tot, groups=rows)
        lines.append(f'\n# timing: {tot:,} violating endpoints grouped by launch family -> capture family')
        for r in rows[:40]:
            lines.append(f'{r["launch"]:28s} -> {r["capture"]:28s} n={r["n"]:7d} worst {r["worst_ps"]:12.1f} ps  {r["causes"]}')
    (a.out / 'die_readout.json').write_text(json.dumps(rec, indent=1) + '\n')
    (a.out / 'die_readout.txt').write_text('\n'.join(lines) + '\n')
    render(a.out / 'die_readout_congestion.png', insts, cells, fl, spots, a.title, a.top)
    print('\n'.join(lines[:a.top + 2]))


if __name__ == '__main__':
    main()
