#!/usr/bin/env python3
"""rc_sum.py RC.json MASTER_PARENT.v : cut-port vs master-pin registration summary of a split piece (PATH-HBM/Q3)."""
import json, re, sys, collections
J = json.load(open(sys.argv[1]))['ports']
txt = open(sys.argv[2]).read()
mp = set(re.findall(r'^\s*(?:input|output)\s+(?:\[\d+:\d+\]\s*)?([A-Za-z_]\w*)\s*;', txt, re.M))
S = collections.defaultdict(collections.Counter); bad = []
for pn, v in J.items():
    kind = 'master' if pn in mp else 'cut'
    for c, n in v['classes'].items():
        ok = (c in ('reg', 'const', 'unused') if v['direction'] == 'output' else c in ('reg', 'unused', 'ff-ctl:CLK') or pn.startswith('clk') or 'clk' in pn or 'rst' in pn)
        S[(kind, v['direction'], 'ok' if ok else 'NOT-REG')][c] += n
        if not ok and kind == 'cut':
            bad.append((pn, v['direction'], c, n))
for k, v in sorted(S.items()):
    print(k, sum(v.values()), dict(v.most_common(6)))
print('cut ports not registered:', len(bad), sum(x[3] for x in bad))
for b in bad[:40]:
    print('  ', b)
