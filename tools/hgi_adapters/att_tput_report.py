#!/usr/bin/env python3
"""hbm-attn-tput2 (2026-10-12): ATT throughput report from a tb_hgi_att_tput run (run_att_tput.sh <out>).

Reads <out>/run.log (REC <case> <j> op <op> disp <c> ret <c>; case <c>: ... <n> wrong) and <out>/vec/tput_cases.json.
Two numbers per record:
  latency   disp -> ret of the record (handshake to rec_done)
  service   the retire-to-retire interval to the previous record of the SAME op in the case's stream (records are
            dispatched as soon as the unit takes them); the first record of an op streak has no service number.
THE GATE is the steady-state service: every service interval <= 1.10 x the record's simulator price (and 0 wrong).
usage: att_tput_report.py <out> [--json <file>] [--extra k=v ...]
"""
import argparse
import json
import re
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--json')
    ap.add_argument('--extra', nargs='*', default=[])
    a = ap.parse_args()
    out = Path(a.out)
    meta = json.loads((out / 'vec' / 'tput_cases.json').read_text())
    log = (out / 'run.log').read_text()
    recs, wrong = {}, {}
    for m in re.finditer(r'REC (\d+) (\d+) op (\d+) disp (\d+) ret (\d+)', log):
        c, j, op, d, r = map(int, m.groups())
        recs.setdefault(c, {})[j] = (op, d, r)
    for m in re.finditer(r'case (\d+): \d+ records in \d+ cycles, \d+ words, (\d+) wrong', log):
        wrong[int(m.group(1))] = int(m.group(2))
    rows, ok = [], ('HGI_ATT_TPUT PASS' in log and 'FAIL' not in log)
    for c, cm in enumerate(meta):
        rs = recs.get(c, {})
        if len(rs) != len(cm['records']):
            ok = False
        for j in sorted(rs):
            op, d, r = rs[j]
            info = cm['records'][j]
            prev = rs.get(j - 1)
            svc = (r - prev[2]) if prev and prev[0] == op else None
            row = dict(case=cm['name'], fmt=cm.get('fmt'), T=cm['T'], j=j, op=op, kind=('qk', 'pv')[op],
                       tag=info['tag'], disp=d, ret=r, latency=r - d, price=info['price'],
                       latency_ratio=round((r - d) / info['price'], 3), service=svc,
                       service_ratio=None if svc is None else round(svc / info['price'], 3),
                       mismatch=wrong.get(c))
            rows.append(row)
            if svc is not None and svc > 1.10 * info['price']:
                ok = False
        if wrong.get(c, 1) != 0:
            ok = False
    summ = {}
    for r in rows:
        k = f"{r['case']}.{r['kind']}"
        s = summ.setdefault(k, dict(T=r['T'], price=r['price'], latency=[], service=[]))
        s['latency'].append(r['latency'])
        if r['service'] is not None:
            s['service'].append(r['service'])
    for k, s in summ.items():
        s['latency_max'] = max(s['latency'])
        s['service_max'] = max(s['service']) if s['service'] else None
        s['service_ratio_max'] = round(s['service_max'] / s['price'], 3) if s['service'] else None
        s['latency_ratio_max'] = round(s['latency_max'] / s['price'], 3)
        print(f"{k:16s} T {s['T']:4d} price {s['price']:7.1f}  latency {s['latency']} (max {s['latency_ratio_max']}x)"
              f"  service {s['service']} (max {s['service_ratio_max']}x)")
    rep = dict(pass_=ok, gate='steady-state service (retire-to-retire interval of same-op records in a back-to-back '
                              'stream, first record of each op excluded) <= 1.10 x price, 0 wrong; latency = disp->ret '
                              'reported, not gated', summary=summ, records=rows)
    for kv in a.extra:
        k, v = kv.split('=', 1)
        rep[k] = v
    print('ATT_TPUT_GATE', 'PASS' if ok else 'FAIL')
    if a.json:
        Path(a.json).write_text(json.dumps(rep, indent=1) + '\n')


if __name__ == '__main__':
    main()
