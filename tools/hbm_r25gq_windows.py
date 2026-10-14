#!/usr/bin/env python3
"""WINDOW congestion check of an HBM R25GQ die model: routing demand against tracks per 2-D window.

Why (v12 GRT verdict, 2026-10-13): the bits-per-cut table (tools/hbm_r25gq_cuts.py) passed at worst 0.502 while the
die global route overflowed by 524,552 bundle tracks, 91 % of it in the hub and most of that in ONE corner
(x 12-15 / y 14-17 mm).  A cut line is 2.4-6 mm long and averages a 1-mm corner away; it also counts a bus on the
straight line between its two end boxes, so the wires that must turn in the corner (N link chains coming down the
spine | slice gap and turning E, the SW SU <-> VM buses, the NW lane group, the TKM stream) are each counted on one
line only.  This check counts wire LENGTH per direction in every window, which is what a global router pays.

Model
  demand    every die hop (driver pin -> load pin of a bus, tools/hbm_accel_die_fp.py pin_points; the nearest points
            of the two boxes when an end has no pin plan) is routed as its two L shapes, half the bits on each; the
            horizontal and the vertical wire length (bit um) are binned on a BIN-um grid.  Clock trunks and the reset
            tree are not counted (as in the cut table).
  capacity  per bin and direction, the track um the die GRT has there (its own layer adjustments, read from the v12
            case): H = M4 x 0.50 + M6 x 0.95 + M8 x 0.7744, V = M5 x 0.50 + M7 x 0.95 + M9 x 0.7744; under a block
            (any non-relay instance over 4e4 um2, as in the cut table) only M8 / M9 remain.  Relay tiles and stations
            do not block: their pins take M4 / M5 and the wires that reach them are the demand counted here.
  window    sliding S x S windows (S = 500, 1,000, 2,000 um, step S / 2): util = demand / capacity per direction.
            LIMIT per size (calibrated on the v12 GRT map, see --grt): a window passes at <= limit in both directions.

  python3 tools/hbm_r25gq_windows.py --ds-var r25gqn_v13 --out results/arch/hier_contract_1011/r25gq_v13_windows
  python3 tools/hbm_r25gq_windows.py --model m.pkl --out ...   (pickle written by --dump-model: boxes + pin segments)
  ... --grt gcell_usage.txt     compare with a die GRT's own overflow map (calibration; writes the comparison)
  ... --hot 12000,14000,15000,17000    print the window's demand by net family
"""
from __future__ import annotations

import argparse
import collections
import json
import pickle
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BIN = 108.0
# tracks per um of cross-section and the share the die GRT leaves to signals (set_global_routing_layer_adjustment of
# the die case: M4 / M5 0.5, M6 / M7 0.05, M8 / M9 0.2256)
LAYERS = dict(H=(('M4', 1 / 0.048, 0.50, True), ('M6', 1 / 0.064, 0.95, True), ('M8', 1 / 0.080, 0.7744, False)),
              V=(('M5', 1 / 0.048, 0.50, True), ('M7', 1 / 0.064, 0.95, True), ('M9', 1 / 0.080, 0.7744, False)))
BLOCK_MIN_UM2 = 4e4
SIZES = (500.0, 1000.0, 2000.0)
# pass limits per window size: a small window may run fuller than a large one (the router spreads into its
# neighbours); calibrated on the v12 die GRT (see results/arch/hier_contract_1011/r25gq_v12_windows.md)
LIMIT = {500.0: 0.90, 1000.0: 0.75, 2000.0: 0.60}
SKIP_CLS = ('clock_trunk', 'reset_tree')


def fam(bid):
    return re.sub(r'\d+', '#', re.sub(r'(_\d+)?(_e)?(_[twqr]\d+(n\d+)?)*$', '', bid))[:28]


def light(m, pins=None):
    """boxes {name: (x0, y0, x1, y1, kind, master)} and hop segments [(bus, cls, bits, x1, y1, x2, y2)]"""
    if isinstance(m['insts'], dict):
        I = {n: (v[2], v[3], v[2] + v[4], v[3] + v[5], v[1], v[0]) for n, v in m['insts'].items()}
    else:
        I = {i.name: (i.x, i.y, i.x + i.w, i.y + i.h, i.kind, i.master) for i in m['insts']}
    if m.get('segs') is not None:
        return I, m['segs']
    cl = lambda bx, q: (min(max(q[0], bx[0]), bx[2]), min(max(q[1], bx[1]), bx[3]))
    segs = []
    for bid, cls, bits, eps in m['buses']:
        ends = [e for e in eps if e[0] in I]
        if cls in SKIP_CLS or len(ends) < 2:
            continue
        a = I[ends[0][0]]
        pa = pins(*ends[0]) if pins else None
        for e in ends[1:]:
            b = I[e[0]]
            pb = pins(*e) if pins else None
            ca, cb = ((a[0] + a[2]) / 2, (a[1] + a[3]) / 2), ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
            p = pa or cl(a, cl(b, ca))
            q = pb or cl(b, cl(a, cb))
            segs.append((bid, cls, bits, p[0], p[1], q[0], q[1]))
    return I, segs


def grid(I):
    W = max(b[2] for b in I.values() if b[4] != 'waypoint') + 20.0
    H = max(b[3] for b in I.values() if b[4] != 'waypoint') + 20.0
    return int(np.ceil(W / BIN)), int(np.ceil(H / BIN))


def capacity(I, nx, ny):
    """(capH, capV, open share) per bin in track um; a block leaves M8 / M9 only"""
    cov = np.zeros((nx, ny))
    for b in I.values():
        if b[4] == 'waypoint' or (b[2] - b[0]) * (b[3] - b[1]) <= BLOCK_MIN_UM2:
            continue
        i0, i1 = int(b[0] // BIN), min(nx - 1, int(b[2] // BIN))
        j0, j1 = int(b[1] // BIN), min(ny - 1, int(b[3] // BIN))
        ox = np.array([max(0.0, min(b[2], (i + 1) * BIN) - max(b[0], i * BIN)) for i in range(i0, i1 + 1)])
        oy = np.array([max(0.0, min(b[3], (j + 1) * BIN) - max(b[1], j * BIN)) for j in range(j0, j1 + 1)])
        cov[i0:i1 + 1, j0:j1 + 1] += np.outer(ox, oy) / (BIN * BIN)
    opn = 1.0 - np.clip(cov, 0.0, 1.0)
    cap = {}
    for d, ls in LAYERS.items():
        cap[d] = sum(t * s * (opn if ch else 1.0) for _n, t, s, ch in ls) * BIN * BIN
    return cap['H'], cap['V'], opn


def _run(arr, fixed, a, b, w, horizontal, nmax):
    """add w bit um per um along [a, b] at the fixed coordinate"""
    if b < a:
        a, b = b, a
    if b - a < 1e-6:
        return
    f = min(nmax[1] - 1, max(0, int(fixed // BIN)))
    k0, k1 = max(0, int(a // BIN)), min(nmax[0] - 1, int(b // BIN))
    for k in range(k0, k1 + 1):
        ln = min(b, (k + 1) * BIN) - max(a, k * BIN)
        if ln > 0:
            if horizontal:
                arr[k, f] += w * ln
            else:
                arr[f, k] += w * ln


def demand(segs, nx, ny, keep=None):
    dH, dV = np.zeros((nx, ny)), np.zeros((nx, ny))
    for s in segs:
        bid, cls, bits, x1, y1, x2, y2 = s
        if keep is not None and not keep(s):
            continue
        h = bits / 2.0
        _run(dH, y1, x1, x2, h, True, (nx, ny))
        _run(dH, y2, x1, x2, h, True, (nx, ny))
        _run(dV, x1, y1, y2, h, False, (ny, nx))
        _run(dV, x2, y1, y2, h, False, (ny, nx))
    return dH, dV


def windows(dH, dV, cH, cV, size):
    """[(util, dir, x0, y0, demand, cap)] of every size x size window, step size / 2"""
    n = max(1, int(round(size / BIN)))
    st = max(1, n // 2)
    out = []
    cs = lambda a: np.pad(a.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    S = {k: cs(v) for k, v in dict(dH=dH, dV=dV, cH=cH, cV=cV).items()}
    nx, ny = dH.shape
    box = lambda c, i, j: c[i + n, j + n] - c[i, j + n] - c[i + n, j] + c[i, j]
    for i in range(0, nx - n + 1, st):
        for j in range(0, ny - n + 1, st):
            for d in 'HV':
                dm, cp = box(S['d' + d], i, j), box(S['c' + d], i, j)
                if cp > 0:
                    out.append((dm / cp, d, i * BIN, j * BIN, dm, cp))
    return out


def by_family(segs, win, nx, ny):
    """demand bit um per family inside the window, both directions"""
    x0, y0, x1, y1 = win
    c = collections.Counter()
    for bid, cls, bits, ax, ay, bx, by in segs:
        if max(ax, bx) < x0 or min(ax, bx) > x1 or max(ay, by) < y0 or min(ay, by) > y1:
            continue
        ov = lambda lo, hi, a, b: max(0.0, min(hi, max(a, b)) - max(lo, min(a, b)))
        ln = 0.0
        for yy in (ay, by):
            if y0 <= yy <= y1:
                ln += ov(x0, x1, ax, bx) / 2
        for xx in (ax, bx):
            if x0 <= xx <= x1:
                ln += ov(y0, y1, ay, by) / 2
        if ln > 0:
            c[fam(bid)] += bits * ln
    return c


def grt_map(path, nx, ny):
    """die GRT overflow (bundle tracks x 16 = bit tracks) per BIN, by direction, from gcell_usage.txt (4 x 4 gcell blocks)"""
    gx = gy = None
    oH, oV = np.zeros((nx, ny)), np.zeros((nx, ny))
    for ln in open(path):
        if ln.startswith('GRIDX'):
            gx = [int(v) / 1000 for v in ln.split()[1].split(',')]
        elif ln.startswith('GRIDY'):
            gy = [int(v) / 1000 for v in ln.split()[1].split(',')]
        elif ln.startswith('L '):
            f = ln.split()
            lay, j = f[1], int(f[2])
            if lay in ('M2', 'M3'):
                continue
            tgt = oH if lay in ('M4', 'M6', 'M8') else oV
            y = gy[min(j + 2, len(gy) - 1)]
            for n, cu in enumerate(f[3:]):
                c, u = cu.split('/')
                o = float(u) - float(c)
                if o > 0:
                    x = gx[min(4 * n + 2, len(gx) - 1)]
                    tgt[min(nx - 1, int(x // BIN)), min(ny - 1, int(y // BIN))] += o
    return oH, oV


def route_cost(dH, dV, cH, cV, geo, prev=None, cell=100.0, win=500.0, u0=0.60, gain=4.0, cap=24.0):
    """(ny, nx) cost per route cell of tools/hbm_r25gq_plan.py's grid (CELL um) for the generator's V['cong']: the
    PathFinder history term.  u = the larger direction's demand / tracks of the win-um window centred on the cell;
    a cell over u0 adds gain x (u - u0) / (1 - u0) to what the previous rounds charged (prev)."""
    from scipy import ndimage as ndi
    import math
    n = max(1, int(round(win / BIN)))
    sm = lambda a: ndi.uniform_filter(a, size=n, mode='constant')
    u = np.maximum(sm(dH) / np.maximum(sm(cH), 1e-9), sm(dV) / np.maximum(sm(cV), 1e-9))       # (nx, ny) on BIN
    nx, ny = math.ceil(geo['W'] / cell), math.ceil(geo['H'] / cell)
    xi = np.minimum(u.shape[0] - 1, ((np.arange(nx) + 0.5) * cell // BIN).astype(int))
    yj = np.minimum(u.shape[1] - 1, ((np.arange(ny) + 0.5) * cell // BIN).astype(int))
    uc = u[np.ix_(xi, yj)].T                                                                  # (ny, nx)
    add = gain * np.maximum(0.0, uc - u0) / (1.0 - u0)
    out = add if prev is None else prev + add
    return np.minimum(out, cap), float(uc.max()), int((uc > u0).sum())


def run(I, segs, sizes=SIZES, top=12):
    nx, ny = grid(I)
    cH, cV, opn = capacity(I, nx, ny)
    dH, dV = demand(segs, nx, ny)
    res = dict(bin_um=BIN, grid=[nx, ny], hops=len(segs), limits={f'{int(s)}': LIMIT[s] for s in sizes}, sizes={})
    worst_fail = 0
    for s in sizes:
        w = sorted(windows(dH, dV, cH, cV, s), reverse=True)
        over = [x for x in w if x[0] > LIMIT[s]]
        worst_fail += len(over)
        rows = []
        for u, d, x0, y0, dm, cp in w[:top]:
            f = by_family(segs, (x0, y0, x0 + s, y0 + s), nx, ny).most_common(5)
            tot = sum(by_family(segs, (x0, y0, x0 + s, y0 + s), nx, ny).values()) or 1.0
            rows.append(dict(util=round(u, 3), dir=d, x_um=[round(x0), round(x0 + s)], y_um=[round(y0), round(y0 + s)],
                             demand_bit_um=round(dm), tracks_um=round(cp), top=[(k, round(v / tot, 3)) for k, v in f]))
        res['sizes'][f'{int(s)}'] = dict(windows=len(w), over=len(over), worst=round(w[0][0], 3) if w else 0.0, top=rows)
    res['verdict'] = 'PASS' if worst_fail == 0 else 'FAIL'
    return res, (dH, dV, cH, cV, opn)


def markdown(res, title, notes=()):
    o = [f'# {title}', '',
         'Model: `tools/hbm_r25gq_windows.py` (every die hop pin to pin as its two L shapes, half the bits each; wire '
         'length per direction per window against the die GRT\'s own track supply: M4 / M5 x 0.50, M6 / M7 x 0.95, '
         'M8 / M9 x 0.7744, blocks leave M8 / M9 only).', '',
         f'**{res["verdict"]}**: ' + ', '.join(f'{k}-um windows {v["over"]} of {v["windows"]} over {res["limits"][k]:.2f} '
                                                f'(worst {v["worst"]:.3f})' for k, v in res['sizes'].items()), '']
    o += [f'- {n}' for n in notes] + ([''] if notes else [])
    for k, v in res['sizes'].items():
        o += [f'## {k}-um windows (limit {res["limits"][k]:.2f})', '',
              '| util | dir | x um | y um | demand bit um | track um | largest families (share) |', '|---:|---|---|---|---:|---:|---|']
        for r in v['top']:
            o.append(f"| {'**' if r['util'] > res['limits'][k] else ''}{r['util']:.3f}{'**' if r['util'] > res['limits'][k] else ''} "
                     f"| {r['dir']} | {r['x_um'][0]:,}-{r['x_um'][1]:,} | {r['y_um'][0]:,}-{r['y_um'][1]:,} | {r['demand_bit_um']:,} "
                     f"| {r['tracks_um']:,} | {', '.join(f'{a} {b:.0%}' for a, b in r['top'])} |")
        o.append('')
    return '\n'.join(o) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--ds-var', default='r25gqn_v13')
    ap.add_argument('--model', type=Path)
    ap.add_argument('--dump-model', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--title', default='')
    ap.add_argument('--note', action='append', default=[])
    ap.add_argument('--grt', type=Path, help='gcell_usage.txt of a die GRT of the same placement: compare')
    ap.add_argument('--hot', default='', help='x0,y0,x1,y1 um: print the window\'s demand by family')
    ap.add_argument('--box', action='store_true', help='box nearest points instead of the pin plans')
    ap.add_argument('--cost-out', type=Path, help='write the route-cell cost (.npy) for the generator (V["cong"])')
    ap.add_argument('--cost-in', type=Path, help='the cost the model was built with (history; summed into --cost-out)')
    a = ap.parse_args(argv)
    if a.model:
        m = pickle.loads(a.model.read_bytes())
        I, segs = light(m)
    else:
        sys.path.insert(0, str(ROOT / 'tools'))
        sys.argv = [sys.argv[0]]
        import hbm_accel_die_fp as F
        m = F.build(F.variant_arg(a.ds_var))
        I, segs = light(m, None if a.box else F.pin_points(m, 16))
        if a.dump_model:
            a.dump_model.write_bytes(pickle.dumps(dict(
                insts={i.name: (i.master, i.kind, i.x, i.y, i.w, i.h, i.orient) for i in m['insts']}, buses=m['buses'],
                segs=segs, geo=m['geo'], phys=m.get('phys_relays'))))
    res, (dH, dV, cH, cV, opn) = run(I, segs)
    nx, ny = dH.shape
    if a.hot:
        win = tuple(float(v) for v in a.hot.split(','))
        c = by_family(segs, win, nx, ny)
        tot = sum(c.values()) or 1.0
        i0, i1, j0, j1 = int(win[0] // BIN), int(win[2] // BIN), int(win[1] // BIN), int(win[3] // BIN)
        res['hot'] = dict(window_um=win, util_H=round(float(dH[i0:i1, j0:j1].sum() / cH[i0:i1, j0:j1].sum()), 3),
                          util_V=round(float(dV[i0:i1, j0:j1].sum() / cV[i0:i1, j0:j1].sum()), 3),
                          families=[(k, round(v / tot, 3)) for k, v in c.most_common(15)])
    if a.cost_out:
        prev = np.load(a.cost_in) if a.cost_in else None
        cst, umax, nover = route_cost(dH, dV, cH, cV, m['geo'], prev)
        np.save(a.cost_out, cst)
        res['route_cost'] = dict(file=str(a.cost_out), history=str(a.cost_in) if a.cost_in else None, cells_over=nover,
                                 util_max_500um=round(umax, 3), cost_max=round(float(cst.max()), 2))
    if a.grt:
        oH, oV = grt_map(a.grt, nx, ny)
        n = int(round(1000.0 / BIN))
        rows = []
        for i in range(0, nx - n + 1, n):
            for j in range(0, ny - n + 1, n):
                sl = (slice(i, i + n), slice(j, j + n))
                ov = float((oH[sl].sum() + oV[sl].sum()) * 16)
                uh, uv = float(dH[sl].sum() / cH[sl].sum()), float(dV[sl].sum() / cV[sl].sum())
                rows.append((ov, max(uh, uv), uh, uv, i * BIN, j * BIN))
        tot = sum(r[0] for r in rows) or 1.0
        cmp_ = {}
        for lim in (0.5, 0.6, 0.7, 0.75, 0.8, 0.9, 1.0):
            fl = [r for r in rows if r[1] > lim]
            cmp_[f'{lim:.2f}'] = dict(flagged=len(fl), grt_overflow_share=round(sum(r[0] for r in fl) / tot, 3),
                                      flagged_with_no_overflow=sum(1 for r in fl if r[0] < 0.001 * tot))
        rows.sort(reverse=True)
        res['grt_compare'] = dict(gcell_usage=str(a.grt), grt_overflow_bit_tracks=round(tot), windows_1mm=len(rows), by_limit=cmp_,
                                  top_grt=[dict(x=round(r[4]), y=round(r[5]), grt_overflow=round(r[0]), util_H=round(r[2], 3),
                                                util_V=round(r[3], 3)) for r in rows[:16]])
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.with_suffix('.json').write_text(json.dumps(dict(variant=a.ds_var, **res), indent=1) + '\n')
    a.out.with_suffix('.md').write_text(markdown(res, a.title or f'R25GQ {a.ds_var}: window congestion', a.note))
    print(json.dumps(dict(verdict=res['verdict'], **{k: dict(over=v['over'], worst=v['worst']) for k, v in res['sizes'].items()},
                          hot=res.get('hot'), grt=res.get('grt_compare', {}).get('by_limit'))))
    return 0 if res['verdict'] == 'PASS' else 3


if __name__ == '__main__':
    raise SystemExit(main())
