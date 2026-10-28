#!/usr/bin/env python3
"""TOK-ALL-17: re-solve the L0 op DAG (schedule.json ops + deps) with RTL-measured gu/vs latencies.

Longest path over the compiled dep graph; each op keeps its compiled cycles unless a measured override applies.
Usage: resolve_measured_dag.py schedule.json overrides.json out.json
overrides.json: {"<op id>": {"cycles": new} | {"delta": d}, ...} with a 'why' per entry.
"""
import json
import sys
from collections import defaultdict

s = json.load(open(sys.argv[1]))
ov = json.load(open(sys.argv[2]))
ops = {o['id']: o for o in s['ops']}
deps = s['deps'] if isinstance(s['deps'], list) else eval(s['deps'])
pred = defaultdict(list)
for d in deps:
    pred[d['dst']].append(d['src'])


def solve(cyc):
    end, start = {}, {}

    def f(i):
        if i in end:
            return end[i]
        st = max([f(p) for p in pred[i]] or [ops[i]['start'] if not pred[i] else 0.0])
        start[i] = st
        end[i] = st + cyc[i]
        return end[i]
    for i in ops:
        f(i)
    return start, end


base = {i: float(o['cycles']) for i, o in ops.items()}
meas = dict(base)
for i, v in ov.items():
    if i.startswith('_'):
        continue
    assert i in ops, i
    meas[i] = float(v['cycles']) if 'cycles' in v else base[i] + float(v['delta'])
s0, e0 = solve(base)
s1, e1 = solve(meas)
span0, span1 = max(e0.values()), max(e1.values())


def crit(end, start, cyc):
    i = max(end, key=end.get)
    path = [i]
    while pred[i]:
        i = max(pred[i], key=lambda p: end[p])
        path.append(i)
    return path[::-1]


rec = dict(schema='opentallas.token_pass.l0_resolve.v1', source=sys.argv[1], compiled_price_span=s['price']['span'],
           resolved_span_compiled_cycles=round(span0, 1), resolved_span_measured=round(span1, 1),
           delta=round(span1 - span0, 1), overrides=ov,
           critical_path_measured=crit(e1, s1, meas),
           ops=[dict(id=i, cyc_compiled=base[i], cyc_used=meas[i], start=round(s1[i], 1), end=round(e1[i], 1),
                     slack_vs_span=None) for i in ops])
# per-op slack (latest finish - end) on the measured DAG
succ = defaultdict(list)
for d in deps:
    succ[d['src']].append(d['dst'])
lf = {}


def latest(i):
    if i in lf:
        return lf[i]
    lf[i] = min([latest(j) - meas[j] for j in succ[i]] or [span1])
    return lf[i]


for r in rec['ops']:
    r['slack'] = round(latest(r['id']) - r['end'], 1)
json.dump(rec, open(sys.argv[3], 'w'), indent=1)
print(f"compiled price span {s['price']['span']}  re-solved(compiled cycles) {span0:.1f}  re-solved(measured) {span1:.1f}  "
      f"delta {span1 - span0:+.1f}")
for i, v in ov.items():
    if not i.startswith('_'):
        r = next(x for x in rec['ops'] if x['id'] == i)
        print(f"  {i}: {base[i]} -> {meas[i]}  slack {r['slack']}")
print('critical:', ' > '.join(x.replace('L0.', '') for x in rec['critical_path_measured']))
