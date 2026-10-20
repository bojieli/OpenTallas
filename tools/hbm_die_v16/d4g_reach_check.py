#!/usr/bin/env python3
"""HBM-GENREACH 10-20: post-GEN reach check of a die case, PER BUS (release rule 2 / SAFE-DESIGN item 2).

    d4g_reach_check.py CASE_DIR CONTRACT [--reach 405] [--tol 0] [--out reach_check.json] [--fix reach_fix.json]

A BUS = (driver instance, driver port base, load instance, load port base); its span = the max placed-pin Manhattan
distance over its bits (real LEF pins of the case views, die.v connectivity; die_relay_pass.load_case, clocks excluded).
Every bus over the reach is classified:
  sync          registered single-cycle stage -> stage (hbfd_rly / land / block pins)        FAILS the case
  fwd           forwarded half-cycle hop between hbfd_lh* stages (and lh -> landing)        FAILS the case
  reset         POR / reset fan-out (por_*, rst*, 'rs' pins): the H.RST regional forest replaces these nets in the
                pre-forest case; reported, does not fail a pre-forest case (--reset-fails makes it fail)
and, for sync / fwd, by cause:
  not_inserted  the PLANNED positions (lane row site 'site (x, y) um', relay 'home (x, y) um', block = placed pin) are
                already over reach + 64.8 um: the relay layer never inserted enough stations (station planner fix)
  placement     planned <= reach + 64.8 but placed over reach: GEN moved a lane row / relay off its planned site
Counts are per bus, never per bit (the census counts a 624-bit hop 624 times).  Exit 1 if any sync / fwd bus is over.
--fix writes the per-bus station requirement for the relay layer / static schedule: extra = ceil(span / reach) - 1
stations on that hop; cost +1 cycle per sync station, +1/2 cycle per forwarded (half-cycle) station.
"""
import argparse
import collections
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'hbm_die_v15'))
import die_relay_pass as RP  # noqa: E402

SITE = re.compile(r'site \(([-\d.]+), ([-\d.]+)\) um')
HOME = re.compile(r'home \(([-\d.]+), ([-\d.]+)\) um')
RST = re.compile(r'(^|_)(rst|reset|por)(_|n|$)|rst_n|_rstn|^rs$')


def classify(case, contract, reach=405.0, tol=0.0, plan_tol=64.8, top=40, strict_coverage=True):
    C = json.loads(Path(contract).read_text()); I = C['instances']
    coverage = {} if strict_coverage else None
    pl, nets, directions, top_inputs = RP.load_case(Path(case), C, coverage=coverage)

    def planned(inst, xy):
        note = I.get(inst, {}).get('note', '') or ''
        m = SITE.search(note)
        if m:
            return (float(m.group(1)), float(m.group(2)))
        m = HOME.search(note)
        if m:
            v = pl[inst]
            return (float(m.group(1)) + v['w'] / 2, float(m.group(2)) + v['h'] / 2)
        return xy
    bus = {}
    for n, ends in nets.items():
        if len(ends) < 2 or n in top_inputs:
            continue
        drv = [e for e in ends if directions.get(e[:2]) == 'OUTPUT']
        lds = [e for e in ends if directions.get(e[:2]) == 'INPUT']
        if len(drv) != 1 or not lds:
            continue
        d0 = drv[0]
        for l in lds:
            s = RP.md(d0[2], l[2])
            k = (d0[0], RP.base(d0[1]), l[0], RP.base(l[1]))
            b = bus.get(k)
            if b is None:
                bus[k] = b = dict(bits=0, span=0.0, dxy=d0[2], lxy=l[2])
            b['bits'] += 1
            if s > b['span']:
                b.update(span=s, dxy=d0[2], lxy=l[2])
    over = collections.Counter(); cause = collections.Counter(); grp = collections.defaultdict(collections.Counter)
    fails, resets, fix = [], 0, []
    hist = collections.Counter()
    for (di, dp, li, lp), b in bus.items():
        if b['span'] <= reach + tol:
            continue
        dm, lm = pl[di]['master'], pl[li]['master']
        if RST.search(dp.lower()) or RST.search(lp.lower()):
            over['reset'] += 1; resets += 1
            continue
        fwd = dm.startswith('hbfd_lh') and lm.startswith(('hbfd_lh', 'hbfd_land'))
        c = 'fwd' if fwd else 'sync'
        ps = RP.md(planned(di, b['dxy']), planned(li, b['lxy']))
        why = 'not_inserted' if ps > reach + plan_tol else 'placement'
        over[c] += 1; cause[f'{c}_{why}'] += 1
        hist['405-810' if b['span'] <= 810 else '810-2000' if b['span'] <= 2000 else '>2000'] += 1
        grp[f'{c}_{why}'][f"{re.sub(r'_(EW|WE|NS|SN).*', '', dm)}.{dp} -> {re.sub(r'_(EW|WE|NS|SN).*', '', lm)}"] += 1
        extra = math.ceil(b['span'] / reach) - 1
        rec = dict(bus=f'{di}.{dp} -> {li}.{lp}', cls=c, cause=why, span_um=round(b['span'], 1), planned_um=round(ps, 1),
                   bits=b['bits'], driver_master=dm, load_master=lm, driver_rule=pl[di].get('rule', '')[:90],
                   load_rule=pl[li].get('rule', '')[:90])
        fails.append(rec)
        fix.append(dict(bus=rec['bus'], cls=c, cause=why, span_um=rec['span_um'], extra_stations=extra,
                        extra_cycles=(extra * 0.5 if fwd else float(extra))))
    fails.sort(key=lambda r: -r['span_um'])
    res = dict(schema='opentallas.hbm.d4g_reach_check.v1', case=str(case), contract=str(contract), reach_um=reach, tol_um=tol,
               unit='bus = (driver inst, driver port, load inst, load port); span = max bit pin span',
               buses_checked=len(bus), over_buses_by_class=dict(over), over_by_cause=dict(cause), span_hist=dict(hist),
               groups={k: [dict(group=g, buses=n) for g, n in v.most_common(20)] for k, v in grp.items()},
               top=fails[:top], verdict='PASS' if not fails else 'FAIL',
               fix_summary=dict(buses=len(fix), extra_stations=sum(f['extra_stations'] for f in fix),
                                extra_cycles_sum=sum(f['extra_cycles'] for f in fix),
                                worst_bus_extra_cycles=max([f['extra_cycles'] for f in fix] or [0])))
    res['geometry_coverage'] = coverage or dict(verdict='NOT_CHECKED', reason='use --strict-coverage')
    res['strict_coverage'] = strict_coverage
    res['geometry_qualified'] = bool(strict_coverage and coverage and coverage['verdict'] == 'PASS')
    res['native_release_qualified'] = False
    res['qualification'] = ('GEOMETRY_COMPLETE_ONLY; timing/clock/reset/native qualification required'
                            if res['geometry_qualified'] else
                            'DIAGNOSTIC_INCOMPLETE_GEOMETRY; no qualification')
    if strict_coverage and coverage['verdict'] != 'PASS':
        res['verdict'] = 'FAIL'
    return res, fails, fix


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('case'); ap.add_argument('contract')
    ap.add_argument('--reach', type=float, default=405.0); ap.add_argument('--tol', type=float, default=0.0)
    ap.add_argument('--out'); ap.add_argument('--fix'); ap.add_argument('--all', help='write every failing bus here (json)')
    ap.add_argument('--reset-fails', action='store_true', help='post-forest case: reset fan-out over reach also fails')
    ap.add_argument('--strict-coverage', action='store_true', help=argparse.SUPPRESS)
    ap.add_argument('--diagnostic-incomplete-coverage', action='store_true',
                    help='diagnostic only: permit an incomplete geometry scan, always unqualified')
    a = ap.parse_args()
    res, fails, fix = classify(a.case, a.contract, a.reach, a.tol, strict_coverage=not a.diagnostic_incomplete_coverage)
    if a.reset_fails and res['over_buses_by_class'].get('reset'):
        res['verdict'] = 'FAIL'
    print('REACH_CHECK' if not a.diagnostic_incomplete_coverage else 'DIAGNOSTIC_REACH_CHECK', res['verdict'], json.dumps({k: res[k] for k in ('buses_checked', 'over_buses_by_class', 'over_by_cause',
                                                                          'span_hist', 'fix_summary')}))
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1))
    if a.fix:
        Path(a.fix).write_text(json.dumps(dict(schema='opentallas.hbm.d4g_reach_fix.v1', reach_um=a.reach,
                                               rule='extra = ceil(span/reach)-1 stations; +1 cycle (sync) / +0.5 cycle (fwd) each',
                                               buses=fix), indent=None))
    if a.all:
        Path(a.all).write_text(json.dumps(fails))
    sys.exit(0 if res['verdict'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
