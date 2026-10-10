#!/usr/bin/env python3
"""hgi-unitrate: turn a unit bench log into an hgi-e2e report.json (the schema tools/hgi_sim/e2e_calibration.py reads:
pass_, summary, per_unit, records {unit, op, real, disp, ret, cost}), with a 'grade' and the source of every number.
  coll: tb_hgi_coll_pipe log (REC k n .. pf .. disp D ret R) + the price per record (NativeCost shares, ds_L0)
  su:   tb_hgi_su_prod log (REC case j accept A retire R) + su_prod.json (priced per record)"""
import argparse, json, re
from pathlib import Path

COLL_PRICE = [382.7, 382.7, 788.5, 765.4] + [126.2] * 7 + [788.5, 126.2]   # ds_L0 NativeCost (e2e sim_cost per record)


def coll(log, vehicle):
    t = Path(log).read_text()
    recs = []
    for m in re.finditer(r'REC (\d+) n (\d+) pf (\d+) disp (-?\d+) ret (-?\d+)', t):
        k = int(m.group(1))
        recs.append(dict(k=k, unit='COLL', op=1, tag=f'gather{k}', real=1, disp=int(m.group(4)), ret=int(m.group(5)),
                         cost=COLL_PRICE[k % len(COLL_PRICE)]))
    return recs, 'HGI_COLL_PIPE PASS' in t


def su(log, man, unit):
    t = Path(log).read_text()
    cases = json.loads(Path(man).read_text())['cases']
    recs = []
    for m in re.finditer(r'REC (\d+) (\d+) accept (-?\d+) retire (-?\d+)', t):
        c, j = int(m.group(1)), int(m.group(2))
        x = cases[j] if len(cases) > 1 and c == 0 and j > 0 else cases[c if len(cases) > c else 0]
        recs.append(dict(k=len(recs), unit=x['unit'], op=0, tag=x['tag'], real=1, disp=int(m.group(3)),
                         ret=int(m.group(4)), cost=x['priced']))
    return recs, 'HGI_SU_PROD PASS' in t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('kind', choices=['coll', 'su'])
    ap.add_argument('--log', required=True)
    ap.add_argument('--manifest')
    ap.add_argument('--grade', required=True)
    ap.add_argument('--vehicle', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    if a.kind == 'coll':
        recs, ok = coll(a.log, a.vehicle)
    else:
        recs, ok = su(a.log, a.manifest, None)
    # records of one bench case run back to back: disp of a later case is offset after the previous case's last retire
    per = {}
    for r in recs:
        p = per.setdefault(r['unit'], dict(records=0, real=0, exact=0, rtl_busy=0, sim_cost=0.0))
        p['records'] += 1; p['real'] += 1; p['exact'] += int(ok); p['sim_cost'] += r['cost']
    out = dict(pass_=ok, grade=a.grade, vehicle=a.vehicle, source_log=a.log,
               summary=dict(cycles=max((r['ret'] for r in recs), default=0), records=len(recs)),
               per_unit=per, records=recs)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1) + '\n')
    print(a.out, ok, len(recs))


if __name__ == '__main__':
    main()
