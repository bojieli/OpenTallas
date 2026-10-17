#!/usr/bin/env python3
"""S81 die MEASURED-reach hop gate (S-DIE H-REACH 2026-10-16; coordinator mandatory item 1: every die hop within MEASURED
reach).  Opt-in from tools/dsrom_s81_fulldie.py --reach-table FILE (default off).

Every data bit between two die instances is judged pin to pin (Manhattan, the same LEF pin geometry as die_hop_gate.py)
against min(reach of the driver class, reach of the load class) from a measured reach table
(results/physical/die_iter_1012/s81/sdie_1815/reach_measured.json, written by relay_reach_bench.py /
relay_native_pair.py).  A hop over that limit, or shorter than a class's measured hold floor, is a HARD error.

Fail closed: a relay / station class (dsfd_(rly|stnh|stnv|hstnh|hstnv|sstn|rstg|xstg)*) on either end of a hop that has
no usable measured entry (missing, status != MEASURED, or usable_as_die_reach_bound false) makes the hop UNMEASURED,
which is also an error.  A hop between two non-relay masters (neither in the relay family) is outside this gate (the flat
--hop-gate / pair gate judge it) and only counted.

    table entry (classes[master]): status 'MEASURED', reach_um (worst-bit pin-to-pin um, stream / TT setup + FF hold +
    electrical), optional gate_reach_um (overrides reach_um), optional hold_min_um, usable_as_die_reach_bound (default
    true when status is MEASURED)
"""
import collections
import json
import re
from pathlib import Path

import die_hop_gate as HG

RELAY_RE = re.compile(r'^dsfd_(rly|stnh|stnv|hstnh|hstnv|sstn|rstg|xstg)(_|$)')


class ReachTableError(ValueError):
    pass


def load_table(path):
    d = json.loads(Path(path).read_text())
    cls = d.get('classes')
    if not isinstance(cls, dict) or not cls:
        raise ReachTableError(f'{path}: no classes{{}} in the reach table')
    out = {}
    for m, r in cls.items():
        ok = r.get('status') == 'MEASURED' and r.get('usable_as_die_reach_bound', True) is not False
        reach = r.get('gate_reach_um', r.get('reach_um'))
        if ok and isinstance(reach, (int, float)) and reach > 0:
            out[m] = dict(reach=float(reach), hold_min=float(r.get('hold_min_um') or 0.0))
        else:
            out[m] = None
    return out


def gate(insts, buses, lef_texts, pslice, table, exempt_cls=HG.EXEMPT_CLS, top=40):
    """-> record dict; verdict FAIL when any bit is over reach, under the hold floor, or touches an unmeasured relay"""
    pins = HG.read_pins(lef_texts)
    by = {it.name: it for it in insts}
    over, under, unmeasured, judged, outside = (collections.Counter() for _ in range(5))
    worst = {}
    missing = 0
    strip = lambda s: re.sub(r'\d+', '#', s)  # noqa: E731

    def entry(master):
        if master in table:
            return 'ok' if table[master] else 'unusable', table[master]
        return ('missing', None) if RELAY_RE.match(master) else ('outside', None)
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
            ma, mb = by[da].master, by[li].master
            (sa, ea), (sb, eb) = entry(ma), entry(mb)
            key = (strip(da) + '.' + dbase, strip(li) + '.' + lbase, ma, mb)
            if sa == 'outside' and sb == 'outside':
                outside[key] += bits
                continue
            if sa in ('missing', 'unusable') or sb in ('missing', 'unusable'):
                unmeasured[key] += bits
                continue
            lims = [e['reach'] for e in (ea, eb) if e]
            floor = max([e['hold_min'] for e in (ea, eb) if e] + [0.0])
            lim = min(lims)
            for b in range(bits):
                pa = HG._loc(by[da], pins, f'{dbase}[{(dlo or 0) + b}]')
                pb = HG._loc(by[li], pins, f'{lbase}[{(llo or 0) + b}]')
                if pa is None or pb is None:
                    missing += 1
                    continue
                L = abs(pa[0] - pb[0]) + abs(pa[1] - pb[1])
                judged[key] += 1
                if L > lim:
                    over[key] += 1
                if L < floor:
                    under[key] += 1
                if L > lim and L - lim > worst.get(key, (0.0,))[0]:
                    worst[key] = (round(L - lim, 1), round(L, 1), lim, bid, da, li)
    rows = sorted(worst.items(), key=lambda kv: -kv[1][0])
    fail = bool(over or under or unmeasured)
    return dict(
        rule='every data bit pin-to-pin <= min(measured reach of its two classes) and >= their hold floor; '
             'relay/station class without a usable measured entry = UNMEASURED = error (tools/s81/die_reach_gate.py)',
        verdict='FAIL' if fail else 'PASS', bits_judged=sum(judged.values()), bits_over_reach=sum(over.values()),
        bits_under_hold_floor=sum(under.values()), bits_unmeasured=sum(unmeasured.values()),
        bits_outside_relay_family=sum(outside.values()), bits_without_pin=missing,
        unmeasured_masters=sorted({m for k in unmeasured for m in k[2:] if entry(m)[0] in ('missing', 'unusable')}),
        worst_over=[dict(drv=k[0], load=k[1], masters=[k[2], k[3]], over_um=v[0], L_um=v[1], limit_um=v[2], bus=v[3],
                         example=[v[4], v[5]], bits_over=over[k]) for k, v in rows[:top]],
        under_hold_floor=[dict(drv=k[0], load=k[1], masters=[k[2], k[3]], bits=n) for k, n in under.most_common(top)])
