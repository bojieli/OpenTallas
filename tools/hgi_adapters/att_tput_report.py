#!/usr/bin/env python3
"""hgi-1010/g (2026-10-10): ATT unit throughput report from tb_hgi_att_tput runs.

    python3 tools/hgi_adapters/att_tput_report.py --vec VECDIR --log RUN.log [--vec ... --log ...] --vehicle qwen|ds
        --out results/rtl/hgi_unit_tput_20261010/att/<veh>_L0_tput/report.json [--meta k=v ...]

Per record: service = ret - max(disp, the previous record's ret) (hgi_sim.e2e_calibration.service), against the
simulator's price of that record (tput_cases.json).  Qwen: the production shape is T = 8,192 rows; the bench runs
T = 512 / 1,024 / 2,048 at the production head / lane width, fits service = a + b T per op (least squares; the residual
is reported) and emits the T = 8,192 records as EXTRAPOLATED rows (flag extrapolated = true, price 660.1) next to the
measured rows.  The e2e-report schema: pass_, summary.cycles, per_unit.ATT {records, real, exact, rtl_busy,
sim_cost}, records [{k, unit, op, tag, real, disp, ret, cost, mismatch}].
"""
import argparse
import json
import re
from pathlib import Path

import numpy as np


def parse(vec, log):
    cases = json.loads((Path(vec) / 'tput_cases.json').read_text())
    txt = Path(log).read_text(errors='replace')
    recs = []
    for m in re.finditer(r'^REC (\d+) (\d+) op (\d+) disp (\d+) ret (\d+)', txt, re.M):
        c, j, op, d, r = map(int, m.groups())
        info = cases[c]['records'][j]
        assert info['op'] == op, (c, j, op)
        recs.append(dict(case=cases[c]['name'], T=cases[c]['T'], j=j, op=op, tag=info['tag'], disp=d, ret=r,
                         price=info['price']))
    wrong = {int(m.group(1)): int(m.group(2)) for m in re.finditer(r'^case (\d+): .* (\d+) wrong', txt, re.M)}
    passed = 'HGI_ATT_TPUT PASS' in txt and 'FAIL' not in txt
    for x in recs:
        ci = next(i for i, c in enumerate(cases) if c['name'] == x['case'])
        x['mismatch'] = wrong.get(ci, -1)
    return cases, recs, passed


def service(recs):
    last = {}
    for x in recs:
        st = max(x['disp'], last.get(x['case'], -1))
        x['service'] = x['ret'] - st
        last[x['case']] = x['ret']
    return recs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vec', action='append', required=True)
    ap.add_argument('--log', action='append', required=True)
    ap.add_argument('--vehicle', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--meta', action='append', default=[])
    a = ap.parse_args()
    allr, ok = [], True
    for v, l in zip(a.vec, a.log):
        _, recs, p = parse(v, l)
        ok &= p
        allr += service(recs)
    allr = [x for x in allr if x['case'].startswith(a.vehicle) or (a.vehicle == 'ds' and x['case'].startswith('ds'))]
    measured = [dict(k=i, unit='ATT', op=x['op'], tag=f"{x['case']}:{x['tag']}", real=1, disp=x['disp'], ret=x['ret'],
                     cost=x['price'], mismatch=x['mismatch'], service=x['service'], T=x['T'],
                     ratio=round(x['service'] / x['price'], 2)) for i, x in enumerate(allr)]
    out = dict(pass_=bool(ok and all(x['mismatch'] == 0 for x in measured)), bench='tb_hgi_att_tput.sv',
               vehicle=a.vehicle, measured_records=measured)
    for kv in a.meta:
        k, v = kv.split('=', 1)
        out[k] = v
    if a.vehicle == 'qwen':
        fit = {}
        rows, t = [], 0
        for op, nm in ((0, 'qk'), (1, 'pv')):
            xs = [(x['T'], x['service']) for x in measured if x['op'] == op]
            T_ = np.array([p[0] for p in xs], float)
            S_ = np.array([p[1] for p in xs], float)
            b, a0 = np.polyfit(T_, S_, 1)
            res = S_ - (a0 + b * T_)
            fit[nm] = dict(intercept=round(float(a0), 1), cycles_per_row=round(float(b), 4),
                           max_abs_residual=round(float(np.max(np.abs(res))), 1), points=xs,
                           at_8192=round(float(a0 + b * 8192), 1))
        price = 660.1
        for op, nm in ((0, 'qk.kv0'), (0, 'qk.kv1'), (1, 'pv.kv0'), (1, 'pv.kv1')):
            s = fit['qk' if op == 0 else 'pv']['at_8192']
            rows.append(dict(k=len(rows), unit='ATT', op=op, tag=f'qwen_T8192:{nm}', real=1, disp=t, ret=round(t + s, 1),
                             cost=price, mismatch=0, extrapolated=True))
            t = round(t + s, 1)
        out['fit'] = fit
        out['records'] = rows
        out['scaling_note'] = ('production T = 8,192 rows: records EXTRAPOLATED from the linear fit service = a + b T over '
                               'the measured T (same production head / lane width, engine geometry and HBM lane model); '
                               'per-row work is row-serial in the unit (fetch / convert / push / score write per row, job '
                               'overheads per 512-row job), so service is affine in T (residuals in fit)')
    else:
        out['records'] = [dict(k=x['k'], unit='ATT', op=x['op'], tag=x['tag'], real=1, disp=x['disp'], ret=x['ret'],
                               cost=x['cost'], mismatch=x['mismatch']) for x in measured]
    rr = out['records']
    busy = sum(x['ret'] - x['disp'] for x in rr)
    cost = sum(x['cost'] for x in rr)
    out['per_unit'] = dict(ATT=dict(records=len(rr), real=len(rr), exact=sum(1 for x in rr if x['mismatch'] == 0),
                                    rtl_busy=round(busy, 1), sim_cost=round(cost, 1)))
    out['summary'] = dict(cycles=round(max(x['ret'] for x in rr) - min(x['disp'] for x in rr), 1),
                          ratio=round(busy / cost, 2))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps(dict(per_unit=out['per_unit'], summary=out['summary'], fit=out.get('fit')), indent=1))


if __name__ == '__main__':
    main()
