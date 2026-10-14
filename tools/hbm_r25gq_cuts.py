#!/usr/bin/env python3
"""Bits-per-cut table of an HBM R25GQ die model (owner 2026-10-12: every cut <= 0.55-0.60 before RTL).

Capacity model = results/arch/hbm_b2_1012/cuts_v07.py (SPEC.md section 6a): a cut line of length L carries, per
direction, 0.75 of the top die layer over its whole length (M8 for horizontal wires, M9 for vertical ones: they run
over the blocks) plus, on the part of the line not covered by a block, 0.75 of M6 / M7 and 0.5 of M4 / M5.

Counting differs from cuts_v07 in one point, on purpose.  cuts_v07 joined block CENTRES, so a line through a block's
body counted every bus that ends in that block (its y = 16 mm line read 0.77 for that reason and had to be explained
away).  Here a bus segment is the segment between the NEAREST POINTS of its two end boxes, i.e. the wire leaves a
block on the face toward its peer; a line is crossed only when it separates those two points.  No artifact lines.

Cuts: the cuts_v07 hub lines, the two full centre lines, the channel on each side of every slot named in --around,
and the SM column channels (cut C of the SM.MATVEC x plane: N-S flow in a column channel, window = the channel plus
half an SM on each side; the channel-only figure 18.2 tracks/um of docs hbm_smmv_xp_spec is printed beside it).

  python3 tools/hbm_r25gq_cuts.py --ds-var r25gqn_v12 --out results/arch/hier_contract_1011/r25gq_v12_cuts
  python3 tools/hbm_r25gq_cuts.py --model m.pkl --out ...      (a pickled {insts: {name: (master, kind, x, y, w, h, ..)}, buses})
"""
from __future__ import annotations

import argparse
import collections
import json
import pickle
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TPU = {'M4': 1 / 0.048, 'M5': 1 / 0.048, 'M6': 1 / 0.064, 'M7': 1 / 0.064, 'M8': 1 / 0.080, 'M9': 1 / 0.080}
LIMIT = 0.60
BLOCK_MIN_UM2 = 4e4          # as cuts_v07: smaller instances (relays, stations, clock pairs) do not close a channel
CHAN_ONLY_TPU = 18.2         # hbm_smmv_xp_spec: 50 % of the two channel layers of one direction


def light(m):
    """{name: (x0, y0, x1, y1, kind, master)}, buses from a build() model or a pickled light model"""
    if isinstance(m['insts'], dict):
        I = {n: (v[2], v[3], v[2] + v[4], v[3] + v[5], v[1], v[0]) for n, v in m['insts'].items()}
    else:
        I = {i.name: (i.x, i.y, i.x + i.w, i.y + i.h, i.kind, i.master) for i in m['insts']}
    return I, m['buses']


def near_pts(a, b):
    """nearest points of two boxes (the wire's ends), found by two projections of the centres"""
    ca, cb = ((a[0] + a[2]) / 2, (a[1] + a[3]) / 2), ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
    cl = lambda bx, q: (min(max(q[0], bx[0]), bx[2]), min(max(q[1], bx[1]), bx[3]))
    p, q = cl(a, cb), cl(b, ca)
    return cl(a, q), cl(b, p)


def capacity(ax, lo, hi, cp, blocks):
    """usable tracks of the cut line (ax 'x': vertical line at x = cp, horizontal wires)"""
    iv = sorted((max(lo, b[1]), min(hi, b[3])) if ax == 'x' else (max(lo, b[0]), min(hi, b[2]))
                for b in blocks if ((b[0] < cp < b[2]) if ax == 'x' else (b[1] < cp < b[3])))
    cov, cur = 0.0, None
    for a, b_ in (v for v in iv if v[1] > v[0]):
        if cur is None or a > cur[1]:
            if cur:
                cov += cur[1] - cur[0]
            cur = [a, b_]
        else:
            cur[1] = max(cur[1], b_)
    cov += (cur[1] - cur[0]) if cur else 0.0
    L, Lch = hi - lo, hi - lo - cov
    top, mid, low = ('M8', 'M6', 'M4') if ax == 'x' else ('M9', 'M7', 'M5')
    return 0.75 * L * TPU[top] + 0.75 * Lch * TPU[mid] + 0.5 * Lch * TPU[low], Lch


def crossing(I, buses, ax, cp, lo, hi):
    """(bits, bits by class, bits by family) of the data buses crossing the line inside [lo, hi]"""
    tot, byc, byf = 0, collections.Counter(), collections.Counter()
    for bid, cls, bits, eps in buses:
        if cls in ('clock_trunk', 'reset_tree'):
            continue
        ends = [I[e[0]] for e in eps if e[0] in I]
        if len(ends) < 2:
            continue
        for z in ends[1:]:
            (x1, y1), (x2, y2) = near_pts(ends[0], z)
            a1, a2, o1, o2 = (x1, x2, y1, y2) if ax == 'x' else (y1, y2, x1, x2)
            if not min(a1, a2) < cp < max(a1, a2):
                continue
            o = o1 + (cp - a1) / (a2 - a1) * (o2 - o1)
            if lo <= o <= hi:
                tot += bits
                byc[cls] += bits
                byf[re.sub(r'(_\d+)?(_e)?(_t\d+)?(_r\d+)*$', '', bid)[:24]] += bits
    return tot, byc, byf


def cut_list(I, around):
    W = max(b[2] for b in I.values() if b[4] != 'waypoint') + 20.0
    H = max(b[3] for b in I.values() if b[4] != 'waypoint') + 20.0
    cuts = collections.OrderedDict()
    cuts['X_centre_full'] = ('x', W / 2, 0.0, H, 'full die')
    cuts['Y_centre_full'] = ('y', H / 2, 0.0, W, 'full die')
    for xc in (12000, 13000, 14000, 14400, 15000, 15500, 16000, 16500, 17000, 18000):
        cuts[f'x{xc / 1000:g}_hub'] = ('x', float(xc), 10000.0, 16000.0, 'hub line (cuts_v07)')
    for yc in (10000, 11000, 12000, 12500, 13000, 14000, 14600, 15000, 16000):
        cuts[f'y{yc / 1000:g}_hub'] = ('y', float(yc), 12000.0, 18000.0, 'hub line (cuts_v07)')
    blocks = [b for b in I.values() if b[4] != 'waypoint' and (b[2] - b[0]) * (b[3] - b[1]) > BLOCK_MIN_UM2]
    for n in around:
        if n not in I:
            continue
        x0, y0, x1, y1 = I[n][:4]
        # the channel on each side: the line midway to the nearest block on that side (<= 1 mm away), over the slot's
        # extent + 500 um each way
        for side, ax in (('W', 'x'), ('E', 'x'), ('S', 'y'), ('N', 'y')):
            if ax == 'x':
                nb = [b[2] if side == 'W' else b[0] for b in blocks if b[1] < y1 and b[3] > y0 and
                      (b[2] <= x0 + 1e-3 if side == 'W' else b[0] >= x1 - 1e-3)]
                edge = x0 if side == 'W' else x1
            else:
                nb = [b[3] if side == 'S' else b[1] for b in blocks if b[0] < x1 and b[2] > x0 and
                      (b[3] <= y0 + 1e-3 if side == 'S' else b[1] >= y1 - 1e-3)]
                edge = y0 if side == 'S' else y1
            if not nb:
                continue
            o = max(nb) if side in 'WS' else min(nb)
            if abs(o - edge) > 1000.0 or abs(o - edge) < 1.0:
                continue
            lo, hi = (y0 - 500.0, y1 + 500.0) if ax == 'x' else (x0 - 500.0, x1 + 500.0)
            cuts[f'{n}_{side}'] = (ax, (o + edge) / 2, lo, hi, f'{abs(o - edge):.0f}-um channel {side} of {n}')
    # SM column channels (cut C): between x-adjacent SMs of one row, a horizontal line at the SM row centre
    sms = sorted((b for b in I.values() if b[4] == 'sm'), key=lambda b: (b[1], b[0]))
    for a in sms:
        right = [b for b in sms if abs(b[1] - a[1]) < 1.0 and b[0] > a[2] and b[0] - a[2] < 600.0]
        if not right:
            continue
        b = min(right, key=lambda q: q[0])
        yc = (a[1] + a[3]) / 2
        half = (a[2] - a[0]) / 2
        cuts[f'C_x{a[2] / 1000:.1f}_y{yc / 1000:.1f}'] = ('y', yc, a[2] - half, b[0] + half,
                                                           f'SM column channel {a[2]:.0f}-{b[0]:.0f} (cut C), +- half an SM',
                                                           (a[2], b[0]))
    return cuts, blocks


def run(m, around=()):
    I, buses = light(m)
    cuts, blocks = cut_list(I, around)
    res = collections.OrderedDict()
    for cn, c in cuts.items():
        ax, cp, lo, hi, what = c[:5]
        tot, byc, byf = crossing(I, buses, ax, cp, lo, hi)
        cap, lch = capacity(ax, lo, hi, cp, blocks)
        r = dict(axis=ax, pos_um=round(cp, 1), span_um=[round(lo, 1), round(hi, 1)], what=what, bits=tot, tracks=round(cap),
                 channel_um=round(lch, 1), util=round(tot / cap, 3), top=byf.most_common(5), by_class=dict(byc.most_common(6)))
        if len(c) > 5:      # cut C: the channel-only figure
            ch0, ch1 = c[5]
            t2, bc2, _ = crossing(I, buses, ax, cp, ch0, ch1)
            r['channel_only'] = dict(span_um=[round(ch0, 1), round(ch1, 1)], bits=t2, tracks=round((ch1 - ch0) * CHAN_ONLY_TPU),
                                     ratio=round(t2 / ((ch1 - ch0) * CHAN_ONLY_TPU), 3), by_class=dict(bc2.most_common(6)))
        res[cn] = r
    return res


def markdown(res, title, notes=()):
    worst = max(res.values(), key=lambda r: r['util'])
    o = [f'# {title}', '',
         'Model: `tools/hbm_r25gq_cuts.py` (capacity of results/arch/hbm_b2_1012 SPEC 6a: 0.75 of M8 / M9 over the whole '
         'line + 0.75 of M6 / M7 and 0.5 of M4 / M5 in its channels; a bus crosses a line when the line separates the '
         'nearest points of its two end boxes).', '',
         f'**{len(res)} cuts, worst {worst["util"]:.3f}, limit {LIMIT:.2f}: '
         f'{"PASS" if worst["util"] <= LIMIT else "FAIL"}**', '']
    o += [f'- {n}' for n in notes] + ([''] if notes else [])
    o += ['| cut | line | window um | what | bits | tracks | util | largest buses |', '|---|---|---|---|---:|---:|---:|---|']
    for cn, r in res.items():
        o.append(f"| {cn} | {r['axis']} = {r['pos_um']:,.0f} | {r['span_um'][0]:,.0f}-{r['span_um'][1]:,.0f} | {r['what']} | "
                 f"{r['bits']:,} | {r['tracks']:,} | {'**' if r['util'] > LIMIT else ''}{r['util']:.3f}"
                 f"{'**' if r['util'] > LIMIT else ''} | {', '.join(f'{a} {b:,}' for a, b in r['top'][:3])} |")
    cc = {k: r for k, r in res.items() if 'channel_only' in r}
    if cc:
        o += ['', '## SM column channels, channel-only figure (stations and channel-layer wires only, 18.2 tracks/um)', '',
              'Informative: the die criterion is the table above (the die routes over the SMs on M8 / M9).', '',
              '| cut | channel um | bits in the channel | tracks | ratio | classes |', '|---|---|---:|---:|---:|---|']
        for cn, r in cc.items():
            c = r['channel_only']
            o.append(f"| {cn} | {c['span_um'][0]:,.0f}-{c['span_um'][1]:,.0f} | {c['bits']:,} | {c['tracks']:,} | {c['ratio']:.2f} | "
                     f"{', '.join(f'{a} {b:,}' for a, b in c['by_class'].items())} |")
    return '\n'.join(o) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--ds-var', default='r25gqn_v12')
    ap.add_argument('--model', type=Path, help='pickled light model instead of building --ds-var')
    ap.add_argument('--around', default='hb_tkm,hb_coll,hb_cmdproc,hb_quant,hb_dbk_SW,hb_dbk_SE,hb_dbk_NW,hb_dbk_NE,'
                    'hb_vms_SW,hb_vms_SE,hb_vms_NW,hb_vms_NE')
    ap.add_argument('--out', type=Path, required=True, help='output stem (.json and .md)')
    ap.add_argument('--title', default='')
    ap.add_argument('--note', action='append', default=[])
    ap.add_argument('--dump-model', type=Path, help='also write the light model pickle (--model input of this tool and '
                    'of tools/hbm_die_rly_kits.py --map)')
    a = ap.parse_args(argv)
    if a.model:
        m = pickle.loads(a.model.read_bytes())
    else:
        sys.path.insert(0, str(ROOT / 'tools'))
        sys.argv = [sys.argv[0]]
        import hbm_accel_die_fp as F
        m = F.build(F.variant_arg(a.ds_var))
        if a.dump_model:
            a.dump_model.write_bytes(pickle.dumps(dict(
                insts={i.name: (i.master, i.kind, i.x, i.y, i.w, i.h, i.orient) for i in m['insts']}, buses=m['buses'],
                geo=m['geo'], phys=m.get('phys_relays'))))
    res = run(m, [n for n in a.around.split(',') if n])
    worst = max(res.values(), key=lambda r: r['util'])
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.with_suffix('.json').write_text(json.dumps(dict(variant=a.ds_var, limit=LIMIT, worst=worst['util'],
                                                          verdict='PASS' if worst['util'] <= LIMIT else 'FAIL', cuts=res),
                                                     indent=1) + '\n')
    a.out.with_suffix('.md').write_text(markdown(res, a.title or f'R25GQ {a.ds_var}: bits per cut', a.note))
    print(json.dumps(dict(cuts=len(res), worst=worst['util'], over=[k for k, r in res.items() if r['util'] > LIMIT])))
    return 0 if worst['util'] <= LIMIT else 3


if __name__ == '__main__':
    raise SystemExit(main())
