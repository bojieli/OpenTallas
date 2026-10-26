#!/usr/bin/env python3
"""Relay / node pin-FACE audit of a die (S-DIE-RELAYFACE 2026-10-16; VIS-ROM S81F-01/03/06/07/08, D-S81-02).

pin_align.py judges each bundle's jog and order; it reports a u-turn only per (driver master.port -> load master.port)
class with one example.  This audit counts, per relay / node MASTER and per instance bundle, whether the pin face of
the master looks toward its peer:

  input bundle  (driver pin D -> this master's input pin I on face f):  behind = -(D - I) . n(f)
  output bundle (this master's output pin O on face f -> load pin L):  behind = -(L - O) . n(f)

  facing away  behind > TOL_UM (1 um): the peer sits behind the face plane, so the bundle has to wrap around the tile
  wrap         behind > the tile depth along n(f): the peer is behind the whole tile (the bus wraps past the far face)
  wrap_um      the largest behind distance (how far the wire has to come back)

Pins are the real LEF pin rectangles (generated abstracts, bound views, hard macros), centroid of the bundle's bits,
instance orientation applied (pin_align.place).  Clock / reset classes are not bundles; the col_reset nets are
reported separately as terminals per net (D-S81-02: one 451-terminal net per column) with the registered depth of a
--col-reset-tree.

Library:  audit(insts, buses, lef_texts=None, pins=None, prefixes=PREFIXES) -> record
          insts: objects with name / master / x / y / orient (the generator's Inst, or rows of a plan / die model)
          buses: (id, class, bits, [(inst, port), ...]) with the driver first
CLI:      relay_face_audit.py MODEL.json[.gz] --lef A.lef [--lef B.lef ...] [--out REC.json] [--top 40]
          MODEL = tools/budgets/extract_die.py die model (clock/model.json.gz of a die chain: insts rows
          [name, master, kind, region, domain, x, y, w, h, orient]) or a pin_align plan ([name, master, x, y, orient]).
"""
from __future__ import annotations

import argparse
import collections
import gzip
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hier_contract'))
import pin_align as PA  # noqa: E402

SCHEMA = 'opentallas.s81.relay_face_audit.v1'
PREFIXES = ('dsfd_rly_', 'dsfd_node_')
TOL_UM = 1.0
CLOCK_CLS = ('clock_trunk', 'clock', 'col_clock', 'fclk', 'top_in', 'top_out', 'reset', 'reset_tree', 'col_reset')
RESET_CLS = ('col_reset',)
_PSL = re.compile(r'^(.*)\[(\d+):(\d+)\]$')


class _I:
    __slots__ = ('name', 'master', 'x', 'y', 'orient')

    def __init__(self, name, master, x, y, orient='R0'):
        self.name, self.master, self.x, self.y, self.orient = name, master, float(x), float(y), orient


def _rows_to_insts(rows):
    out = []
    for r in rows:
        if isinstance(r, dict):
            out.append(_I(r['name'], r['master'], r['x'], r['y'], r.get('orient', 'R0')))
        elif len(r) >= 10:                       # die model: name, master, kind, region, domain, x, y, w, h, orient
            out.append(_I(r[0], r[1], r[5], r[6], r[9]))
        else:                                    # pin_align plan: name, master, x, y, orient
            out.append(_I(*r[:5]))
    return out


def _base(port):
    mm = _PSL.match(port)
    return (mm.group(1), int(mm.group(2)), int(mm.group(3))) if mm else (port, None, None)


class _Pins:
    """port centroid (die frame) and face of an instance port, from read_pins tables; cached per master/port slice"""

    def __init__(self, pins):
        self.pins = pins
        self.cache = {}

    def local(self, master, port, bits):
        key = (master, port, bits)
        if key in self.cache:
            return self.cache[key]
        w, h, pp = self.pins.get(master, (0.0, 0.0, {}))
        base, lo, hi = _base(port)
        lo = lo or 0
        n = bits if hi is None else hi - lo + 1
        pts = [pp.get(f'{base}[{lo + i}]') for i in range(n)]
        pts = [q for q in pts if q is not None]
        if not pts and pp.get(base) is not None:
            pts = [pp[base]]
        if not pts:
            self.cache[key] = None
            return None
        faces = collections.Counter(q[2] for q in pts)
        f = faces.most_common(1)[0][0]
        x = sum(q[0] for q in pts) / len(pts)
        y = sum(q[1] for q in pts) / len(pts)
        res = (w, h, (x, y, f, pts[0][3]))
        self.cache[key] = res
        return res

    def at(self, it, port, bits):
        loc = self.local(it.master, port, bits)
        if loc is None:
            return None
        w, h, q = loc
        X, Y, f, _ = PA.place(it, w, h, q)
        return X, Y, f, w, h


def _depth(f, w, h):
    return w if f in 'EW' else h


def audit(insts, buses, lef_texts=None, pins=None, prefixes=PREFIXES, top=40, tol_um=TOL_UM):
    by = {it.name: it for it in insts}
    if pins is None:
        pins = PA.read_pins(lef_texts or [], {it.master for it in insts})
    P = _Pins(pins)
    rows = collections.defaultdict(lambda: dict(bundles=0, bits=0, away=0, away_bits=0, wrap=0, wrap_bits=0,
                                                wrap_um=0.0, no_face=0, worst=None))
    resets = {}
    mine = lambda m: m.startswith(prefixes)

    def note(key, behind, bits, depth, ex):
        r = rows[key]
        r['bundles'] += 1
        r['bits'] += bits
        if behind is None:
            r['no_face'] += 1
            return
        if behind > tol_um:
            r['away'] += 1
            r['away_bits'] += bits
            if behind > depth + tol_um:
                r['wrap'] += 1
                r['wrap_bits'] += bits
            if behind > r['wrap_um']:
                r['wrap_um'] = round(behind, 1)
                r['worst'] = ex

    for bid, cls, bits, eps in buses:
        c0 = cls.split('@')[0]
        if c0 in RESET_CLS:
            resets[str(bid)] = len(eps)
            continue
        if c0 in CLOCK_CLS:
            continue
        ie = [(i, q) for i, q in eps if i in by]
        if len(ie) < 2:
            continue
        (da, dp), loads = ie[0], ie[1:]
        ia = by[da]
        pa = None
        for li, lp in loads:
            ib = by[li]
            dm, lm = mine(ia.master), mine(ib.master)
            if not (dm or lm):
                continue
            if pa is None:
                pa = P.at(ia, dp, bits) or (None,)
            pb = P.at(ib, lp, bits)
            if pa[0] is None or pb is None:
                for flag, it_, p_ in ((dm, ia, dp), (lm, ib, lp)):
                    if flag:
                        note((it_.master, 'out' if it_ is ia else 'in', _base(p_)[0]), None, bits, 0, None)
                continue
            dX, dY, df, dw, dh = pa
            lX, lY, lf, lw, lh = pb
            if lm:
                if lf is None:
                    note((ib.master, 'in', _base(lp)[0]), None, bits, 0, None)
                else:
                    n = PA.NORMAL[lf]
                    behind = -((dX - lX) * n[0] + (dY - lY) * n[1])
                    note((ib.master, 'in', _base(lp)[0]), behind, bits, _depth(lf, lw, lh),
                         dict(bus=str(bid), inst=li, face=lf, peer=f'{da}.{_base(dp)[0]}', peer_master=ia.master,
                              at=[round(lX, 1), round(lY, 1)], peer_at=[round(dX, 1), round(dY, 1)]))
            if dm:
                if df is None:
                    note((ia.master, 'out', _base(dp)[0]), None, bits, 0, None)
                else:
                    n = PA.NORMAL[df]
                    behind = -((lX - dX) * n[0] + (lY - dY) * n[1])
                    note((ia.master, 'out', _base(dp)[0]), behind, bits, _depth(df, dw, dh),
                         dict(bus=str(bid), inst=da, face=df, peer=f'{li}.{_base(lp)[0]}', peer_master=ib.master,
                              at=[round(dX, 1), round(dY, 1)], peer_at=[round(lX, 1), round(lY, 1)]))
    out_rows = []
    for (mst, d, port), r in rows.items():
        out_rows.append(dict(master=mst, dir=d, port=port, **r,
                             away_pct=round(100.0 * r['away'] / r['bundles'], 1) if r['bundles'] else 0.0))
    out_rows.sort(key=lambda r: (-r['away_bits'], r['master'], r['dir'], r['port']))

    def fam(pfx):
        sel = [r for r in out_rows if r['master'].startswith(pfx)]
        t = collections.Counter()
        for r in sel:
            for k in ('bundles', 'bits', 'away', 'away_bits', 'wrap', 'wrap_bits'):
                t[f"{r['dir']}_{k}"] += r[k]
        res = dict(t)
        for d in ('in', 'out'):
            b = t.get(f'{d}_bundles', 0)
            res[f'{d}_away_pct'] = round(100.0 * t.get(f'{d}_away', 0) / b, 2) if b else 0.0
        res['wrap_um_max'] = max([r['wrap_um'] for r in sel] + [0.0])
        res['masters'] = len({r['master'] for r in sel})
        return res
    rs = sorted(resets.values())
    return dict(schema=SCHEMA, tol_um=tol_um,
                totals={p: fam(p) for p in prefixes},
                masters=out_rows[:top] if top else out_rows,
                masters_total=len(out_rows),
                col_reset=dict(nets=len(rs), max_terminals=rs[-1] if rs else 0,
                               median_terminals=rs[len(rs) // 2] if rs else 0,
                               nets_over_64=sum(1 for v in rs if v > 64), terminals=sum(rs)))


def line(rec):
    t = rec['totals']
    s = []
    for p, v in t.items():
        s.append('%s in %d/%d away (%.1f%%) out %d/%d away (%.1f%%) wrap %d/%d bundles max %.1f um' % (
            p.rstrip('_'), v.get('in_away', 0), v.get('in_bundles', 0), v.get('in_away_pct', 0.0), v.get('out_away', 0),
            v.get('out_bundles', 0), v.get('out_away_pct', 0.0), v.get('in_wrap', 0) + v.get('out_wrap', 0),
            v.get('in_bundles', 0) + v.get('out_bundles', 0), v.get('wrap_um_max', 0.0)))
    cr = rec['col_reset']
    s.append('col_reset nets %d max %d terminals (median %d, >64: %d)' % (cr['nets'], cr['max_terminals'],
                                                                         cr['median_terminals'], cr['nets_over_64']))
    return 'OT_RELAY_FACE ' + '; '.join(s)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('model')
    ap.add_argument('--lef', action='append', default=[])
    ap.add_argument('--out')
    ap.add_argument('--top', type=int, default=60)
    a = ap.parse_args(argv)
    p = Path(a.model)
    d = json.loads(gzip.open(p, 'rt').read() if p.suffix == '.gz' else p.read_text())
    insts = _rows_to_insts(d['insts'])
    buses = [(b[0], b[1], b[2], [tuple(e[:2]) for e in b[3]]) for b in d['buses']]
    texts = []
    for f in a.lef:
        fp = Path(f)
        texts.append(gzip.open(fp, 'rt').read() if fp.suffix == '.gz' else fp.read_text())
    rec = audit(insts, buses, texts, top=a.top)
    rec['model'] = str(p)
    rec['lefs'] = a.lef
    if a.out:
        Path(a.out).write_text(json.dumps(rec, indent=1) + '\n')
    print(line(rec))
    for r in rec['masters'][:a.top]:
        print('%-22s %-3s %-4s bundles %6d away %6d (%5.1f%%) wrap %5d max %7.1f um' % (
            r['master'], r['dir'], r['port'], r['bundles'], r['away'], r['away_pct'], r['wrap'], r['wrap_um']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
