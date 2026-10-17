#!/usr/bin/env python3
"""Build the per-class S81 measured reach table (reach_measured.json) that tools/s81/die_reach_gate.py gates on.

Source of every number: relay_native_pair.py result.json files (composed NATIVE pairs: both CLOSED netlists + routed
SPEF + GRT-measured die wire, real forwarded phase, TT 833 / 1111 setup, FF hold, max_transition 260 + max_cap on every
pin).  A class is MEASURED only when its native result exists and its stream window is valid; otherwise NOT_MEASURED
with the reason (no closed archive, batch failed, ...).  ETM-only (scalar-slew) tables are never used as a bound.

    relay_reach_table.py --stage STAGE --np NP_ROOT [--np NP_ROOT2] [--repeated REP_NP_ROOT ...] --out reach_measured.json
"""
import argparse
import json
import re
from pathlib import Path


def otrun(log):
    if not log.exists():
        return None
    t = log.read_text(errors='ignore')
    m = re.search(r'ot-run: RAN on (\S+) \(unit (\S+)\): exit (\d+)', t)
    return dict(log=str(log), host=m.group(1), unit=m.group(2), exit=int(m.group(3))) if m else dict(log=str(log), state='not completed')


def row_from(res, vn='native'):
    v = res['variants'][vn]
    s, se = v['stream'], v['serial']
    return dict(reach_um=s['reach_L_um'], reach_d_um=s['reach_d_um'], slack_at_reach_ps=s['slack_at_reach_ps'],
                reach_serial_um=se['reach_L_um'], hold_min_um=s['hold_floor_L_um'], window_valid=s['window_valid'],
                first_fail_d_um=s['first_fail_d_um'], first_fail_reason=s['first_fail_reason'],
                reach_um_at_slew320=s['sensitivity_slew320']['reach_L_um'],
                repeaters_at_reach=next((p.get('repeaters') for p in v['points'] if p['d'] == s['reach_d_um']), None))


REPEATER_AREA_UM2 = {'BUFx4_ASAP7_75t_R': 0.0875, 'BUFx4f_ASAP7_75t_R': 0.1021, 'BUFx5_ASAP7_75t_R': 0.1166,
                     'BUFx6f_ASAP7_75t_R': 0.1458, 'BUFx8_ASAP7_75t_R': 0.175}   # ASAP7 RVT width x 0.27 um row


def repeated_summary(res, stg):
    """repeated-wire rows: the largest swept d that passes setup, FF hold and every slew/cap check (points below it that
    fail are listed: the bench's ETM-based repair can leave a marginal hop unrepeated), and repeaters / mm / bit"""
    pts = res['variants']['native']['points']
    ok = lambda p: (p['tt833'] is not None and p['tt833'] >= 0 and p['ff_hold'] is not None and p['ff_hold'] >= 0  # noqa: E731
                    and not p['slew_viol_tt'] and not p['slew_viol_ff'] and not p['cap_viol_tt'] and not p['cap_viol_ff'])
    good = [p for p in pts if ok(p)]
    best = max(good, key=lambda p: p['d']) if good else None
    rep = {v['d']: v for v in stg['points'].values()}
    out = dict(repeated_reach_d_um=best and best['d'], repeated_reach_L_um=best and best['L_max'],
               repeated_slack_ps=best and best['tt833'],
               failing_points_below_reach=[[p['d'], 'setup' if (p['tt833'] or 0) < 0 else 'electrical/hold']
                                           for p in pts if best and p['d'] < best['d'] and not ok(p)])
    if best:
        r = rep[best['d']]
        out['repeaters_per_bit_at_reach'] = round(r['repeaters'] / max(1, r['bits']), 2)
        out['repeaters_per_mm_per_bit'] = round(r['repeaters'] / max(1, r['bits']) / (best['L_max'] / 1000.0), 2)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--stage', required=True)
    ap.add_argument('--np', action='append', required=True, help='unbuffered native pair root(s): <root>/<class>/result.json')
    ap.add_argument('--repeated', action='append', default=[], help='repeated-wire native pair root(s), LAYER=ROOT')
    ap.add_argument('--flag-um', type=float, default=300.0)
    ap.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    st = json.loads((Path(a.stage) / 'stage.json').read_text())['classes']
    out = dict(
        schema='opentallas.s81.relay_reach_measured.v2', date='2026-10-16',
        method=('MEASURED on native cells: tools/s81/relay_native_pair.py composes, per sweep point d, the two CLOSED '
                'native netlists of the class (driver A, receiver B; 6_final.v + routed 6_final.spef) joined bit by bit '
                'by the die wire that OpenROAD global_route laid between the bound views at their real pin faces '
                '(die layer rules M4-M9, estimate_parasitics -global_routing; relay_reach_bench.py --fwd-clock). '
                'OpenSTA: TT setup 833.33 / 1111.1 ps, FF hold, SS 833 sensitivity; stations: one clock at A.fi0 '
                'propagated through A tree -> fo0 -> routed clock wire -> B tree (actual inverted half-cycle phase), '
                'base uncertainty 60/25; die-ck classes: phase-aligned roots + 60/25 + 80 ps neighbour skew. '
                'Electrical: native SDC set_max_transition 260 ps and library max_capacitance on every pin of both '
                'instances. reach_um = worst-bit pin-to-pin Manhattan length at the last swept d (25 um steps) with '
                'setup >= 0 and zero slew/cap violations at that and every shorter d; hold_min_um = shortest length '
                'from which FF hold passes up to the reach. UNBUFFERED unless a row says repeated.'),
        gate_field='reach_um (stream, unbuffered native); die_reach_gate.py reads classes[m].reach_um / hold_min_um',
        classes={})
    found = {}
    for root in a.np:
        for f in Path(root).glob('*/result.json'):
            found.setdefault(f.parent.name, f)
    rep = {}
    for spec in a.repeated:
        lay, root = spec.split('=', 1)
        for f in Path(root).glob('*/result.json'):
            rep.setdefault(f.parent.name, {})[lay] = f
    for m, r in sorted(st.items()):
        row = dict(instances_c26l=r.get('instances_c26l', 0), flow=r.get('flow'), buses=r.get('buses'),
                   view=dict(job=r.get('job'), verdict=r.get('verdict'), **{c: f for c, f in r['files'].items()}))
        if m not in found:
            row.update(status='NOT_MEASURED', reason='no native pair result (closed archive missing/unusable, or batch '
                                                     'not run)', usable_as_die_reach_bound=False)
        else:
            res = json.loads(found[m].read_text())
            stg = json.loads((found[m].parent / 'stage.json').read_text())
            nr = row_from(res)
            row.update(native=dict(job=res['job'], clock_mode=res['clock_mode'], identity=stg.get('identity'),
                                   consumed=stg.get('consumed'), bench_run=stg.get('bench_run'),
                                   result=str(found[m]), sta_job=otrun(found[m].parent.parent / f'{m}.otrun.log')), **nr)
            if len(res['variants']) > 1:
                row['driver_variants'] = {vn: row_from(res, vn) for vn in res['variants']}
            ok = nr['window_valid'] and nr['reach_um']
            row['status'] = 'MEASURED' if ok else 'NOT_MEASURED'
            row['usable_as_die_reach_bound'] = bool(ok)
            if not ok:
                row['reason'] = f'no valid unbuffered window: {nr["first_fail_reason"]}'
            else:
                row['planning_um'] = round(0.9 * nr['reach_um'], 1)
                if nr['reach_um'] < a.flag_um:
                    row['flag'] = 'SHORT-HOP-ONLY'
                    row['flag_note'] = ('unbuffered reach below 300 um: hops must be <= reach (more relays) or the die '
                                        'wire repeated / receiver input rebuilt (see repeated rows)')
        if m in rep:
            row['repeated'] = {}
                for lay, f in rep[m].items():
                res = json.loads(f.read_text())
                stg = json.loads((f.parent / 'stage.json').read_text())
                row['repeated'][lay] = dict(result=str(f), **row_from(res), **repeated_summary(res, stg))
        out['classes'][m] = row
    meas = {m: r for m, r in out['classes'].items() if r['status'] == 'MEASURED'}
    used = {m: r for m, r in out['classes'].items() if r['instances_c26l']}
    out['summary'] = dict(
        classes=len(out['classes']), measured=len(meas), used_in_c26l=len(used),
        used_measured=sum(1 for m in used if m in meas),
        used_not_measured={m: r.get('reason') for m, r in used.items() if m not in meas},
        worst15_instance_weighted=[[m, r['reach_um'], r['instances_c26l'], r.get('first_fail_reason')] for m, r in sorted(
            ((m, r) for m, r in meas.items() if r['instances_c26l']),
            key=lambda kv: (kv[1]['reach_um'], -kv[1]['instances_c26l']))][:15],
        by_instances=[[m, r['instances_c26l'], r['reach_um']] for m, r in sorted(
            meas.items(), key=lambda kv: -kv[1]['instances_c26l'])][:20],
        flagged_below_300=sorted([[m, r['reach_um'], r['instances_c26l'], r['flag']] for m, r in meas.items()
                                  if r.get('flag')], key=lambda x: x[1]),
        min_reach_um_used=min((r['reach_um'] for m, r in meas.items() if r['instances_c26l']), default=None),
        instance_weighted_mean_reach_um=round(sum(r['reach_um'] * r['instances_c26l'] for r in meas.values()) /
                                              max(1, sum(r['instances_c26l'] for r in meas.values())), 1))
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(json.dumps(out['summary'], indent=1)[:3000])


if __name__ == '__main__':
    main()
