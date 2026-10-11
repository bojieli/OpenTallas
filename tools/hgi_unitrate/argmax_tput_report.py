#!/usr/bin/env python3
"""hgi-1010/tput1-argmax: tb_hgi_argmax_tput logs -> report.json (results/rtl/hgi_unit_tput_20261010 unit-report shape:
pass_, grade, vehicle, source_log, summary, records[{k, unit, op, tag, real, disp, ret, cost}]).  Each record runs from
its own dispatch (the bench resets between records: one ARGMAX.LOCAL a token), so disp = 0 and ret = dispatch -> retire.

  python3 tools/hgi_unitrate/argmax_tput_report.py --log PASS.log --cases at_cases.json --mutant-log M1.log M2.log \
      --vehicle TEXT --meta JSON --out report.json
"""
import argparse
import json
import re
from pathlib import Path

REC = re.compile(r"REC (\d+) n (\d+) rank (\d+) disp 0 first (-?\d+) last (-?\d+) ret (\d+) tail (-?\d+)")


def parse(p):
    t = Path(p).read_text()
    return {int(m.group(1)): dict(first=int(m.group(4)), last=int(m.group(5)), ret=int(m.group(6)), tail=int(m.group(7)))
            for m in REC.finditer(t)}, ("HGI_ARGMAX_TPUT PASS" in t), t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--log', required=True)
    ap.add_argument('--cases', required=True)
    ap.add_argument('--mutant-log', nargs='*', default=[])
    ap.add_argument('--vehicle', required=True)
    ap.add_argument('--meta', default='{}')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    cs = json.loads(Path(a.cases).read_text())
    recs, ok, _ = parse(a.log)
    rows = []
    for c in cs['cases']:
        r = recs[c['k']]
        rows.append(dict(k=c['k'], unit='ARGMAX', op=0, tag=c['tag'], real=1, disp=0, ret=r['ret'], cost=c['cost'],
                         first_beat=r['first'], last_beat=r['last'], tail=r['tail'], ratio=round(r['ret'] / c['cost'], 3)))
    muts = []
    for m in a.mutant_log:
        _, mok, mt = parse(m)
        muts.append(dict(log=m, verdict='PASS' if mok else 'FAIL', errors=len(re.findall(r'^ERR', mt, re.M))))
    cyc = sum(x['ret'] for x in rows)
    cost = sum(x['cost'] for x in rows)
    rep = dict(pass_=ok and all(m['verdict'] == 'FAIL' for m in muts), bench_pass=ok, grade='measured_unit_bench',
               vehicle=a.vehicle, source_log=a.log,
               summary=dict(records=len(rows), cycles=cyc, sim_cost=round(cost, 3), ratio=round(cyc / cost, 3),
                            n=cs['n'], imm_a=cs['imm_a'], price_per_record=cs['price'], price_how=cs['price_how'],
                            max_ret=max(x['ret'] for x in rows), max_tail_last_beat_to_retire=max(x['tail'] for x in rows)),
               per_unit=dict(ARGMAX=dict(records=len(rows), real=len(rows), exact=len(rows) if ok else 0,
                                         sim_cost=round(cost, 3))),
               mutants=muts, records=rows)
    rep.update(json.loads(a.meta))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(rep, indent=1) + '\n')
    print(a.out, rep['summary'], 'pass_', rep['pass_'])


if __name__ == '__main__':
    main()
