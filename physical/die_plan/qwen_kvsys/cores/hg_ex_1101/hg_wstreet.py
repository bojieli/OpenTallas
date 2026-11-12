#!/usr/bin/env python3
"""KV hg W-face street (vN2 W-pin-pocket fix, hg family).

usage: hg_wstreet.py PLAN OUT [--dx 43.2] [--types kv3_hg_] [--resite R.json]

In every hg type the W column (head0_e0/e2/e4/e6 + ectl_q0 at x = 17.28) leaves the W-face pins only the 104-129 um gaps
between its cores, which is where the W landing bands (i_slg_Q_N_krsp, ft3_i) pile up into hot pockets (GEOM-VIS-4,
kv3_hg_v1p3, local density 1.385).  This pass MOVES (never re-shapes) the W column east by dx so a full-height W street
opens between the W face and the column; the cores' own taps move with them.  Plan objects the moved cores now cover
are fail-closed by kind: other hard cores, internal stations, the reset tap and foreign clock taps stop the pass;
landing bands, ft regs and collector relays are listed for the landing / collector re-solve (--resite); die clock
islands under the moved cores are removed and listed for the die clock owner (as plan_cut does).
"""
import argparse, copy, importlib.util, json
from pathlib import Path

_s = importlib.util.spec_from_file_location('hg_plan_cut', Path(__file__).with_name('plan_cut.py'))
pc = importlib.util.module_from_spec(_s)
_s.loader.exec_module(pc)

GRID = 8.64
EDGE = 17.28
RESITE_KINDS = ('landing_band', 'ft_reg', 'collector_relay')


def _rect(h, dx=0.0):
    x, y = h['origin_um']
    w, hh = h['outline_um']
    if h.get('orient') in ('R90', 'R270', 'MXR90', 'MYR90'):
        w, hh = hh, w
    return [x + dx, y, x + dx + w, y + hh]


def _own_tap(tp, inst):
    n = tp.get('name', '')
    return n == inst or n.startswith(inst + '.')


def apply(p, dx=43.2, prefix='kv3_hg_'):
    """-> (plan, report rows per type, resite rows)"""
    if abs(dx / GRID - round(dx / GRID)) > 1e-6 or dx <= 0:
        raise ValueError(f'dx {dx}: positive multiple of {GRID}')
    p = copy.deepcopy(p)
    rep, resite = [], []
    for tn, t in sorted(p['partition_types'].items()):
        if not tn.startswith(prefix):
            continue
        col = [h for h in t.get('hard_cores', []) if abs(h['origin_um'][0] - EDGE) < 1e-3]
        if not col:
            raise ValueError(f'{tn}: no W column at x={EDGE}')
        insts = {h['inst'] for h in col}
        ow = t['outline_um'][0]
        rest = copy.deepcopy(t)
        rest['hard_cores'] = [h for h in t['hard_cores'] if h['inst'] not in insts]
        rest['clock']['taps'] = [tp for tp in t['clock'].get('taps', []) if not any(_own_tap(tp, i) for i in insts)]
        moved = []
        for h in col:
            r = _rect(h, dx)
            if r[2] > ow - EDGE + 1e-6:
                raise ValueError(f'{tn} {h["inst"]}: moved core leaves the outline ({r[2]} > {ow - EDGE})')
            for k, n, xy in pc.blockers(rest, r):
                if k in RESITE_KINDS:
                    resite.append(dict(type=tn, kind=k, name=n, at=xy, core=h['inst']))
                else:
                    raise ValueError(f'{tn} {h["inst"]} at {r}: covers {k} {n}')
            moved.append(r)
        street = min((_rect(h)[0] for h in rest['hard_cores'] if _rect(h)[0] > EDGE + 1), default=ow) - max(r[2] for r in moved)
        for h in col:
            h['origin_um'] = [round(h['origin_um'][0] + dx, 3), h['origin_um'][1]]
        for tp in t['clock'].get('taps', []):
            if any(_own_tap(tp, i) for i in insts):
                tp['xy'] = [round(tp['xy'][0] + dx, 3), tp['xy'][1]]
        ck = t['clock']
        isl = ck.get('die_islands_um', [])
        olds = [_rect(h, -dx) for h in col]   # col already moved: old footprint
        cov = lambda r, rs: any(pc._ov(r, q) for q in rs)
        gone = [r for r in isl if cov(r, moved) and not cov(r, olds)]   # newly covered only
        ck['die_islands_um'] = [r for r in isl if r not in gone]
        resite += [dict(type=tn, kind='die_clock_island', rect_um=r) for r in gone]
        t['note'] = (t.get('note') or '') + (f' | KV-HG-SPLIT-1 vN2 W street: W column {sorted(insts)} moved +{dx} um'
                                             f' (move only), W street {dx} um, col1-col2 street {round(street, 2)} um')
        rep.append(dict(type=tn, moved=sorted(insts), w_street_um=dx, col12_street_um=round(street, 2),
                        islands_removed=len(gone)))
    if not rep:
        raise ValueError(f'no {prefix}* types')
    return p, rep, resite


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('plan')
    a.add_argument('out')
    a.add_argument('--dx', type=float, default=43.2)
    a.add_argument('--types', default='kv3_hg_')
    a.add_argument('--resite')
    a = a.parse_args()
    p, rep, rs = apply(json.load(open(a.plan)), a.dx, a.types)
    Path(a.out).write_text(json.dumps(p, indent=1) + '\n')
    if a.resite:
        Path(a.resite).write_text(json.dumps(dict(schema='opentallas.kv.hg_wstreet_resite.v1', types=rep, rows=rs), indent=1) + '\n')
    for r in rep:
        print('HG_WSTREET', r)
    print('HG_WSTREET_RESITE', len(rs), sorted({(r['kind']) for r in rs}))
