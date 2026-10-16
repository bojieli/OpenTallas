#!/usr/bin/env python3
"""KV/system die trial READOUT (owner-asked 2026-10-16, coordinator): every Qwen KV die trial (kvs12a onward) produces

  readout_congestion.png  GRT demand heat map (max over M2-M9 of nets / tracks per 4.8-um gcell, binned) + block outlines
                          (pre-expansion frames, relays as dots) + the top-20 data flows (bits x distance) as arrows
  readout_hotspots.json   every hot spot (connected bins >= --hot) classified with measured numbers and the fix:
                            pin_face_density | partner_placement | channel_metal_margin | clock_relay_structure
  readout_timing.txt      setup / hold failures grouped by block pair and cause (from kvsys_classify.py classify.json)
  readout.md              the three tables, PNG paths

Inputs: the run's case_kv/{place.tcl.preexp, elements.lef.preexp, die.v.preexp} (frames: block-level picture),
case_kv/elements.lef (expanded: pin faces of the real leaves), grt_kv/route.guide (GRT guides: per-gcell demand) and
classify.json.  Demand = nets whose guide covers the gcell; capacity = gcell / track pitch of the layer (ASAP7).  The
guides carry no blockage, so a hot spot over a macro means wires routed OVER it (allowed layers only).

    python3 tools/qwen_kv_die/kv_readout.py --run RUN [--guide G] [--classify C] --out DIR
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import re
from pathlib import Path

import numpy as np

GC = 4.8                      # GRT gcell (um) of the KV die flow (guides are gcell-aligned)
PITCH = dict(M2=0.036, M3=0.036, M4=0.048, M5=0.048, M6=0.064, M7=0.064, M8=0.08, M9=0.08)
LAYERS = list(PITCH)
BIN = 10                      # gcells per display / hot-spot bin (48 um)


def read_place(p):
    pl = {}
    for ln in open(p):
        m = re.search(r'findInst (\S+)\] ([\d.]+) ([\d.]+) (\S+)', ln)
        if m:
            pl[m.group(1)] = (float(m.group(2)), float(m.group(3)), m.group(4))
    return pl


def read_lef(p, faces=False):
    """master -> (w, h[, {face: pins per um}])"""
    out, cur, w, h, pins, pin = {}, None, 0, 0, collections.defaultdict(int), None
    for ln in open(p):
        t = ln.split()
        if not t:
            continue
        if t[0] == 'MACRO':
            cur, pins = t[1], collections.defaultdict(int)
        elif t[0] == 'SIZE' and cur:
            w, h = float(t[1]), float(t[3])
        elif t[0] == 'PIN' and cur:
            pin = t[1]
        elif t[0] == 'RECT' and pin and faces and len(t) >= 5:
            x0, y0, x1, y1 = map(float, t[1:5])
            for f, d in (('W', x0), ('E', w - x1), ('S', y0), ('N', h - y1)):
                if d < 1.0:
                    pins[f] += 1
                    break
            pin = None                       # one rect a pin is enough for the face count
        elif t[0] == 'END' and len(t) > 1 and t[1] == cur:
            dens = {f: round(n / (h if f in 'WE' else w), 3) for f, n in pins.items()} if faces else None
            out[cur] = (w, h, dens)
            cur = None
        elif t[0] == 'END' and pin and len(t) > 1 and t[1] == pin:
            pin = None
    return out


def read_netlist(p):
    """instance -> master, net base -> {instances}, net base -> bits"""
    inst, conn, bits = {}, collections.defaultdict(set), {}
    for ln in open(p):
        m = re.match(r'\s*wire \[(\d+):(\d+)\] (\S+);', ln)
        if m:
            bits[m.group(3)] = int(m.group(1)) - int(m.group(2)) + 1
            continue
        m = re.match(r'\s*(\w+) (\w+) \((.*)\);\s*$', ln)
        if m and m.group(1) not in ('module', 'wire', 'input', 'output'):
            inst[m.group(2)] = m.group(1)
            for n in re.findall(r'\((n_[A-Za-z0-9_]+)', m.group(3)):
                conn[n].add(m.group(2))
    return inst, conn, bits


def is_relay(master):
    return master.startswith(('qkd_rly', 'qkd_rlys'))


def flows(inst, conn, bits, box, top=20):
    """one flow per logical bus (relay hops folded): its non-relay endpoints, bits, centre distance"""
    bus = collections.defaultdict(lambda: [set(), 0])
    for n, s in conn.items():
        if 'clk' in n or n.startswith(('n_rst', 'n_ck')):
            continue
        base = re.sub(r'__r\d+$', '', n)
        b = bus[base]
        b[0] |= {i for i in s if not is_relay(inst.get(i, ''))}
        b[1] = max(b[1], bits.get(n, 1))
    out = []
    for base, (ends, w) in bus.items():
        ends = [e for e in ends if e in box]
        if len(ends) != 2 or w < 2:
            continue
        a, b = sorted(ends)
        ca, cb = centre(box[a]), centre(box[b])
        d = abs(ca[0] - cb[0]) + abs(ca[1] - cb[1])
        out.append(dict(bus=base[2:], a=a, b=b, bits=w, dist_um=round(d, 1), score=w * d))
    out.sort(key=lambda f: -f['score'])
    return out[:top], out


def centre(bx):
    return (bx[0] + bx[2] / 2, bx[1] + bx[3] / 2)


def demand(guide, W, H):
    nx, ny = int(math.ceil(W / GC)) + 2, int(math.ceil(H / GC)) + 2
    dif = {l: np.zeros((ny + 1, nx + 1), np.int32) for l in LAYERS}
    cls = {c: np.zeros((ny + 1, nx + 1), np.int32) for c in ('clock', 'relay', 'data')}
    buf = collections.defaultdict(list)
    net_cls = 'data'

    def flush():
        for (l, c), rs in buf.items():
            a = np.array(rs, np.int64)
            x0 = np.clip(a[:, 0] // 4800, 0, nx - 1); y0 = np.clip(a[:, 1] // 4800, 0, ny - 1)
            x1 = np.clip((a[:, 2] - 1) // 4800 + 1, 1, nx); y1 = np.clip((a[:, 3] - 1) // 4800 + 1, 1, ny)
            for arr in (dif[l], cls[c]):
                np.add.at(arr, (y0, x0), 1); np.add.at(arr, (y1, x0), -1)
                np.add.at(arr, (y0, x1), -1); np.add.at(arr, (y1, x1), 1)
        buf.clear()
    k = 0
    with open(guide) as f:
        for ln in f:
            c0 = ln[0]
            if c0 == '(' or c0 == ')':
                continue
            t = ln.split()
            if len(t) == 1:
                n = t[0]
                net_cls = 'clock' if ('clk' in n or n.startswith(('n_ck', 'n_pll'))) else 'relay' if '__r' in n else 'data'
                continue
            if len(t) == 5 and t[4] in dif:
                buf[(t[4], net_cls)].append((int(t[0]), int(t[1]), int(t[2]), int(t[3])))
                k += 1
                if k % 2_000_000 == 0:
                    flush()
    flush()
    use = {l: np.cumsum(np.cumsum(d, 0), 1)[:ny, :nx] for l, d in dif.items()}
    cl = {c: np.cumsum(np.cumsum(d, 0), 1)[:ny, :nx] for c, d in cls.items()}
    return use, cl, k


def binmax(a, b=BIN):
    ny, nx = a.shape
    a = a[:ny - ny % b, :nx - nx % b]
    return a.reshape(ny // b, b, nx // b, b).max(axis=(1, 3))


def binsum(a, b=BIN):
    ny, nx = a.shape
    a = a[:ny - ny % b, :nx - nx % b]
    return a.reshape(ny // b, b, nx // b, b).sum(axis=(1, 3))


def classify_spot(sp, box, inst, lefx, cl, flows_all):
    """measured numbers around one hot spot and its class + fix"""
    x0, y0, x1, y1 = sp['bbox_um']
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    near = []
    for n, (bx, by, bw, bh) in box.items():
        if is_relay(inst.get(n, '')):
            continue
        dx = max(0.0, bx - x1, x0 - (bx + bw)); dy = max(0.0, by - y1, y0 - (by + bh))
        if dx + dy <= 40.0:
            near.append((dx + dy, n))
    near.sort()
    # pin face density of the nearest real leaves (expanded LEF) facing the spot
    face_best = (0.0, None)
    for d, n in near[:8]:
        bx, by, bw, bh = box[n]
        m = inst.get(n, '')
        dens = (lefx.get(m) or (0, 0, None))[2] or {}
        f = 'E' if cx >= bx + bw else 'W' if cx <= bx else 'N' if cy >= by + bh else 'S'
        if dens.get(f, 0) > face_best[0]:
            face_best = (dens.get(f, 0), f'{n}.{f}')
    # channel: the gap between the nearest blocks left/right (or below/above) of the spot centre
    gx = [b for b in box.values() if b[1] <= cy <= b[1] + b[3]]
    left = max([b[0] + b[2] for b in gx if b[0] + b[2] <= cx] or [0.0])
    right = min([b[0] for b in gx if b[0] >= cx] or [1e9])
    gy = [b for b in box.values() if b[0] <= cx <= b[0] + b[2]]
    below = max([b[1] + b[3] for b in gy if b[1] + b[3] <= cy] or [0.0])
    above = min([b[1] for b in gy if b[1] >= cy] or [1e9])
    chan = min(right - left, above - below)
    sl = (slice(int(y0 / GC), int(y1 / GC) + 1), slice(int(x0 / GC), int(x1 / GC) + 1))
    tot = sum(float(cl[c][sl].sum()) for c in cl) or 1.0
    shares = {c: round(float(cl[c][sl].sum()) / tot, 3) for c in cl}
    crossing = [f for f in flows_all if _crosses(f, box, (x0, y0, x1, y1))]
    crossing.sort(key=lambda f: -f['bits'])
    num = dict(peak_util=sp['peak'], layer=sp['layer'], area_um2=sp['area_um2'], channel_um=round(chan, 1),
               face_pins_per_um=face_best[0], face=face_best[1], share=shares,
               flows_crossing=len(crossing), top_crossing=[f"{f['bus']} {f['bits']}b" for f in crossing[:4]])
    if shares['clock'] + shares['relay'] >= 0.5:
        c_, fix = 'clock_relay_structure', (f"clock+relay nets are {shares['clock'] + shares['relay']:.0%} of the demand: spread "
                                            f"the relay rows / clock repeaters over more channel tracks or move the chain")
    elif face_best[0] >= 8.0:
        c_, fix = 'pin_face_density', (f"{face_best[1]} carries {face_best[0]} pins/um (> 8): spread / split the face "
                                       f"(two layers, more face length) or re-pin the leaf")
    elif chan < 60.0:
        c_, fix = 'channel_metal_margin', f"channel {chan:.1f} um between blocks: widen to >= 60 um or move signals up a layer pair"
    else:
        c_, fix = 'partner_placement', (f"{len(crossing)} data flows cross (largest {num['top_crossing'][:2]}): "
                                        f"place the partners closer / re-route the flow around the spot")
    return c_, num, fix


def _crosses(f, box, r):
    (ax, ay), (bx, by) = centre(box[f['a']]), centre(box[f['b']])
    # L route x first then y: does either leg pass the rectangle
    x0, y0, x1, y1 = r
    leg1 = (min(ax, bx) <= x1 and max(ax, bx) >= x0 and y0 <= ay <= y1)
    leg2 = (min(ay, by) <= y1 and max(ay, by) >= y0 and x0 <= bx <= x1)
    return leg1 or leg2


def timing_table(cfile, top=25):
    d = json.loads(Path(cfile).read_text())
    lines = []
    for cn in ('tt', 'ff'):
        c = d['corners'].get(cn)
        if not c:
            continue
        rows = [r for r in c['rows'] if r['worst_ps'] < 0]
        rows.sort(key=lambda r: r['worst_ps'])
        lines.append(f"== {cn.upper()} ({'setup' if cn == 'tt' else 'hold'}): {sum(r['violators'] for r in rows)} violators in "
                     f"{len(rows)} block-pair groups")
        lines.append(f"{'worst ps':>9} {'viol':>7} {'pin um':>7}  cause / launch -> capture   example")
        for r in rows[:top]:
            why = ('hop > reach' if (r.get('nearest_pin_um') or 0) > 450 else 'long hop' if (r.get('nearest_pin_um') or 0) > 250
                   else 'tile timing (pin/insertion)') if cn == 'tt' else ('model/frame' if 'frame' in r['cause'] or 'relay' in r['cause']
                                                                          else 'real hold')
            lines.append(f"{r['worst_ps']:9.2f} {r['violators']:7d} {r.get('nearest_pin_um') or 0:7.1f}  {r['cause']}: "
                         f"{r['launch']} -> {r['capture']} [{why}]  {r['example']['start']} -> {r['example']['end']}")
    return '\n'.join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', type=Path, required=True)
    ap.add_argument('--guide', type=Path)
    ap.add_argument('--classify', type=Path)
    ap.add_argument('--hot', type=float, default=None, help='hot-spot threshold (demand / tracks of the worst layer); '
                    'default: the 98th percentile of the occupied bins (the guides are gcell boxes, often dilated, so the '
                    'absolute ratio over-counts: GRT overflow, not this ratio, is the capacity verdict)')
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--title', default=None)
    a = ap.parse_args(argv)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, FancyArrowPatch
    from scipy import ndimage

    c = a.run / 'case_kv' if (a.run / 'case_kv').is_dir() else a.run
    a.out.mkdir(parents=True, exist_ok=True)
    pl = read_place(c / 'place.tcl.preexp')
    lef = read_lef(c / 'elements.lef.preexp')
    lefx = read_lef(c / 'elements.lef', faces=True)
    inst, conn, bits = read_netlist(c / 'die.v.preexp')
    box = {}
    for n, (x, y, o) in pl.items():
        m = inst.get(n)
        if m and m in lef:
            w, h, _ = lef[m]
            if o in ('R90', 'R270', 'MXR90', 'MYR90'):
                w, h = h, w
            box[n] = (x, y, w, h)
    W = max(b[0] + b[2] for b in box.values()); H = max(b[1] + b[3] for b in box.values())
    # the expanded case's leaves for the face density lookups (their masters / places)
    instx, _, _ = read_netlist(c / 'die.v')
    plx = read_place(c / 'place.tcl')
    boxx = {n: (x, y, lefx[instx[n]][0], lefx[instx[n]][1]) for n, (x, y, o) in plx.items() if instx.get(n) in lefx}
    top, flows_all = flows(inst, conn, bits, box)

    guide = a.guide or (a.run / 'grt_kv' / 'route.guide')
    use, cl, nrect = demand(guide, W, H)
    util = {l: use[l] / (GC / PITCH[l]) for l in LAYERS}
    stack = np.stack([util[l] for l in LAYERS])
    worst = stack.max(0); worst_l = stack.argmax(0)
    hb = binmax(worst)
    occ = hb[hb > 0]
    a.hot = a.hot if a.hot is not None else float(np.percentile(occ, 98)) if occ.size else 1.0
    vmax = float(np.percentile(occ, 99.5)) if occ.size else 1.0
    lab, n = ndimage.label(hb >= a.hot)
    spots = []
    for k in range(1, n + 1):
        ys, xs = np.nonzero(lab == k)
        y0, y1, x0, x1 = ys.min() * BIN * GC, (ys.max() + 1) * BIN * GC, xs.min() * BIN * GC, (xs.max() + 1) * BIN * GC
        sub = worst[int(y0 / GC):int(y1 / GC), int(x0 / GC):int(x1 / GC)]
        iy, ix = np.unravel_index(int(sub.argmax()), sub.shape)
        lay = LAYERS[int(worst_l[int(y0 / GC) + iy, int(x0 / GC) + ix])]
        spots.append(dict(bbox_um=[round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)], peak=round(float(sub.max()), 3),
                          layer=lay, area_um2=round(len(ys) * (BIN * GC) ** 2)))
    spots.sort(key=lambda s: (-s['peak'], -s['area_um2']))
    for s in spots[:40]:
        s['class'], s['measured'], s['fix'] = classify_spot(s, {**box, **boxx}, {**inst, **instx}, lefx, cl, flows_all)

    # picture
    fig, ax = plt.subplots(figsize=(9, 9 * H / W * 0.55 + 2), dpi=150)
    im = ax.imshow(binmax(worst, 2), origin='lower', extent=(0, binmax(worst, 2).shape[1] * 2 * GC, 0, binmax(worst, 2).shape[0] * 2 * GC),
                   cmap='inferno', vmin=0, vmax=vmax, interpolation='nearest')
    fig.colorbar(im, ax=ax, fraction=0.03, label='GRT guide demand / tracks (worst layer M2-M9; relative)')
    for nme, (x, y, w, h) in box.items():
        if is_relay(inst.get(nme, '')):
            ax.plot(x + w / 2, y + h / 2, ',', color='#44aaff', alpha=0.4)
        else:
            ax.add_patch(Rectangle((x, y), w, h, fill=False, lw=0.4, ec='#7fffd4'))
    for i, f in enumerate(top):
        (ax_, ay_), (bx_, by_) = centre(box[f['a']]), centre(box[f['b']])
        ax.add_patch(FancyArrowPatch((ax_, ay_), (bx_, by_), arrowstyle='-|>', mutation_scale=6,
                                     lw=0.4 + math.log2(f['bits']) / 4, color='#00ff66', alpha=0.85))
        ax.text((ax_ + bx_) / 2, (ay_ + by_) / 2, str(i + 1), color='#00ff66', fontsize=5)
    for j, s in enumerate(spots[:12]):
        x0, y0, x1, y1 = s['bbox_um']
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, lw=0.8, ec='#ff3355'))
        ax.text(x1, y1, f"H{j + 1}", color='#ff3355', fontsize=6)
    ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect('equal')
    ax.set_title(a.title or f'{a.run.name}: GRT demand, blocks, top-20 flows (green), hot spots (red)', fontsize=8)
    png = a.out / 'readout_congestion.png'
    fig.savefig(png, bbox_inches='tight'); plt.close(fig)

    tt = timing_table(a.classify) if a.classify and a.classify.exists() else '(no classify.json)'
    (a.out / 'readout_timing.txt').write_text(tt + '\n')
    rec = dict(schema='opentallas.qwen_kv_readout.v1', run=str(a.run), guide_rects=nrect, die_um=[W, H], hot_threshold=round(a.hot, 3),
               worst_bin_util=round(float(hb.max()), 3),
               layer_peak={l: round(float(binmax(util[l]).max()), 3) for l in LAYERS},
               hotspots=spots[:40], hotspots_total=len(spots), top_flows=top, png=str(png))
    (a.out / 'readout_hotspots.json').write_text(json.dumps(rec, indent=1) + '\n')
    md = [f'# KV die readout {a.run.name}', '', f'PNG: {png}', '',
          f'worst bin demand/tracks {rec["worst_bin_util"]}; hot spots >= {a.hot}: {len(spots)}', '',
          '| # | bbox um | peak | layer | class | measured | fix |', '|---|---|---|---|---|---|---|']
    for j, s in enumerate(spots[:20]):
        m_ = s.get('measured', {})
        md.append(f"| H{j + 1} | {s['bbox_um']} | {s['peak']} | {s['layer']} | {s.get('class')} | chan {m_.get('channel_um')} um, "
                  f"face {m_.get('face')} {m_.get('face_pins_per_um')}/um, clk+rly {m_.get('share', {}).get('clock', 0) + m_.get('share', {}).get('relay', 0):.2f}, "
                  f"{m_.get('flows_crossing')} flows | {s.get('fix')} |")
    md += ['', '## top-20 data flows (bits x centre distance)', '', '| # | bus | a -> b | bits | um |', '|---|---|---|---|---|']
    md += [f"| {i + 1} | {f['bus']} | {f['a']} -> {f['b']} | {f['bits']} | {f['dist_um']} |" for i, f in enumerate(top)]
    md += ['', '## timing by block pair', '', '```', tt, '```']
    (a.out / 'readout.md').write_text('\n'.join(md) + '\n')
    print(f'READOUT {png} hotspots={len(spots)} worst={rec["worst_bin_util"]}')


if __name__ == '__main__':
    main()
