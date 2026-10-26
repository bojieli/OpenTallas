#!/usr/bin/env python3
"""S81 die hop gate (s81-die v14, 2026-10-12): pin-to-pin Manhattan length of every data bit between two die
instances, from the generator's own bus list and the LEFs it wrote (no place run needed).  Hard gate: no data hop may
exceed the limit (default 600 um = --relay-tt-reach; the SS reach 504 um is reported beside it).

c3 (v11) failed TT by -17.7 ns on 2.3-2.4 mm unbuffered HC-hub hops and c5 (v13) still carried a 1,025 um
svc_SW.rv -> ctrl_SW.rd hop and a 717 um wq_d_vm last hop; the post-PLACE lint (die_hop_lint.py) found them after a
12-h GRT.  This gate runs inside `dsrom_s81_fulldie.py real` and fails GEN.

Exempt: clock / reset distribution classes only (they are CTS / reset-tree nets, not register-to-register data).

PER-PAIR LIMIT (pinreg-pairs 2026-10-13): with `pair` (tools/hier_contract/pair_check.py Gate) the limit of a hop is
the reach of ITS two masters from their real views, min(limit_um, (T - 60 - SKEW - o_src - s_dst) / 0.76); a forwarded
link (the load's clock pin is driven by the driver: class 'fclk') takes the forwarded-clock reach.  The flat limit_um (500 um) stays the
limit of every hop whose two masters have no view (generated placeholders) and the ceiling of every other hop.

usage (module): gate(insts, buses, lef_paths, limit_um, exempt_cls, pslice) -> record dict
usage (CLI on a die DEF, same as die_hop_lint): see die_hop_lint.py"""
import collections
import re

ORI = {'R0': 'N', 'MY': 'FN', 'MX': 'FS', 'R180': 'S', 'N': 'N', 'FN': 'FN', 'FS': 'FS', 'S': 'S'}
EXEMPT_CLS = ('clock_trunk', 'reset', 'reset_tree', 'clock', 'col_clock', 'col_reset', 'fclk', 'top_in')


def read_pins(lef_texts):
    """{macro: (w, h, {bitpin: (cx, cy)})} from LEF texts (first rect of each pin)"""
    out = {}
    for t in lef_texts:
        m = None
        pin = None
        for line in t.splitlines():
            s = line.split()
            if not s:
                continue
            if s[0] == 'MACRO':
                m = s[1]
                out[m] = [0.0, 0.0, {}]
            elif m is None:
                continue
            elif s[0] == 'SIZE':
                out[m][0], out[m][1] = float(s[1]), float(s[3])
            elif s[0] == 'PIN':
                pin = s[1]
            elif s[0] == 'RECT' and pin is not None and pin not in out[m][2]:
                x0, y0, x1, y1 = map(float, s[1:5])
                out[m][2][pin] = ((x0 + x1) / 2, (y0 + y1) / 2)
            elif s[0] == 'END' and len(s) > 1:
                if s[1] == pin:
                    pin = None
                elif s[1] == m:
                    m = None
            elif s[0] == 'OBS':
                pin = None
    return out


def _loc(it, pins, bitpin):
    w, h, pp = pins.get(it.master, (0.0, 0.0, {}))
    p = pp.get(bitpin)
    if p is None:
        return None
    px, py = p
    o = ORI.get(it.orient, 'N')
    if o == 'S':
        px, py = w - px, h - py
    elif o == 'FN':
        px = w - px
    elif o == 'FS':
        py = h - py
    return it.x + px, it.y + py


def gate(insts, buses, lef_texts, pslice, limit_um=600.0, ss_um=504.0, exempt_cls=EXEMPT_CLS, top=40, pair=None):
    pins = read_pins(lef_texts)
    by = {it.name: it for it in insts}
    cls_n = collections.Counter()
    worst = {}
    over = collections.Counter()
    over_ss = collections.Counter()
    nbits = 0
    lmax = [0.0]
    missing = 0
    strip = lambda s: re.sub(r'\d+', '#', s)
    lim_of = {}
    pair_over = collections.Counter()
    for bid, cls, bits, eps in buses:
        if cls in exempt_cls:
            continue
        ie = [(i, p) for i, p in eps if i in by]
        if len(ie) < 2:
            continue
        (da, dp), loads = ie[0], ie[1:]
        dbase, dlo, _ = pslice(dp)
        for li, lp in loads:
            lbase, llo, _ = pslice(lp)
            key = (strip(da) + '.' + dbase, strip(li) + '.' + lbase, cls)
            lim = limit_um
            if pair is not None:
                lim = min(limit_um, pair.limit(da, by[da].master, dbase, li, by[li].master, lbase))
                lim_of[key] = min(lim, lim_of.get(key, lim))
            for b in range(bits):
                pa = _loc(by[da], pins, f'{dbase}[{(dlo or 0) + b}]')
                pb = _loc(by[li], pins, f'{lbase}[{(llo or 0) + b}]')
                if pa is None or pb is None:
                    missing += 1
                    continue
                nbits += 1
                L = abs(pa[0] - pb[0]) + abs(pa[1] - pb[1])
                if L > lmax[0]:
                    lmax[0] = L
                if L > lim and lim < limit_um:
                    pair_over[key] += 1
                if L > ss_um or L > lim:
                    over_ss[key] += L > ss_um
                    if L > lim:
                        over[key] += 1
                    if L > worst.get(key, (0.0,))[0]:
                        worst[key] = (L, bid, da, f'{dbase}[{(dlo or 0) + b}]', li, f'{lbase}[{(llo or 0) + b}]',
                                      [round(v) for v in pa + pb])
        cls_n[cls] += 1
    rows = sorted(worst.items(), key=lambda kv: (-over.get(kv[0], 0), -kv[1][0]))
    rec = dict(limit_um=limit_um, ss_reach_um=ss_um,
               pair_check=None if pair is None else dict(
                   table_masters=len(pair.t), pairs=len(pair.pairs), hops=dict(pair.used),
                   bits_over_pair_limit=sum(pair_over.values()),
                   candidates_bound_by_direction=[dict(src=k[0] + '.' + k[1], dst=k[2] + '.' + k[3], limit_um=v) for k, v in sorted(pair.candidates.items(), key=lambda kv: kv[1])][:top],
                   hold_fail=[dict(src=k[0] + '.' + k[1], dst=k[2] + '.' + k[3], model=k[4], hold_ps=v) for k, v in sorted(pair.hold.items(), key=lambda kv: kv[1])],
                   tightest=sorted(((round(v, 1), k[0], k[1]) for k, v in lim_of.items() if v < limit_um))[:top],
                   rule='per pair min(limit_um, reach of the two real views); flat limit_um without views '
                        '(tools/hier_contract/pair_check.py)'), exempt_classes=list(exempt_cls), bits_checked=nbits,
               bits_without_pin=missing, bits_over_limit=sum(over.values()), bits_over_ss=sum(over_ss.values()),
               max_um=round(lmax[0], 1),     # the longest checked data hop (was 0.0 on a PASS: only over-reach classes were ranked)
               verdict='PASS' if not over and not (pair is not None and pair.hold) else 'FAIL',
               classes=[dict(drv=k[0], load=k[1], cls=k[2], limit_um=lim_of.get(k, limit_um), bits_over_limit=over.get(k, 0), bits_over_ss=over_ss[k],
                             max_um=round(v[0], 1), bus=v[1], example=list(v[2:])) for k, v in rows[:top]])
    return rec
