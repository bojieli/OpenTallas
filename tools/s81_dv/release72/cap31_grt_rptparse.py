#!/usr/bin/env python3
"""Compact a GRT congestion report: rptparse.py RPT OUT.json -> list of {d,x0,y0,x1,y1,cap,use,cong,nets:{bus:count}}"""
import sys, re, json, collections
out = []; cur = None
for ln in open(sys.argv[1]):
    s = ln.strip()
    if s.startswith('violation type:'):
        cur = dict(d='H' if 'Horizontal' in s else 'V'); out.append(cur)
    elif s.startswith('srcs:') and cur is not None:
        c = collections.Counter(re.sub(r'\[\d+\]$', '', t[4:]) for t in s[5:].split() if t.startswith('net:'))
        cur['nets'] = dict(c.most_common(12)); cur['nnets'] = sum(c.values())
    elif s.startswith('comment:') and cur is not None:
        m = re.search(r'capacity:(\d+) usage:(\d+) congestion:(\d+)', s)
        if m: cur['cap'], cur['use'], cur['cong'] = map(int, m.groups())
    elif s.startswith('bbox') and cur is not None:
        v = list(map(float, re.findall(r'-?\d+\.?\d*', s.split('on Layer')[0])))
        cur['x0'], cur['y0'], cur['x1'], cur['y1'] = v[:4]
json.dump(out, open(sys.argv[2], 'w'))
print(len(out), sum(e.get('cong', 0) for e in out))
