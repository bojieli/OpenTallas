#!/usr/bin/env python3
"""Attribute GRT congestion report (capped sample) to ft slots: congestion split equally across src nets; per slot: share, bbox."""
import re, sys, collections
for f in sys.argv[1:]:
    tot = 0; n = 0; share = collections.Counter(); box = {}; lay = collections.Counter()
    cur = None
    for line in open(f):
        if line.startswith('\tsrcs:'):
            nets = re.findall(r'net:(\S+)', line)
        elif line.startswith('\tcomment:'):
            c = int(re.search(r'congestion:(\d+)', line).group(1))
        elif line.startswith('\tbbox'):
            x0, y0 = map(float, re.findall(r'\(([\d.]+), ([\d.]+)\)', line)[0])
            n += 1; tot += c
            keys = []
            for nt in nets:
                m = re.match(r'nq_st_([A-Za-z0-9]+)_', nt) or re.match(r'(?:nq_|n_)?([A-Za-z]+[0-9]*[a-z]*[0-9]*)', nt)
                keys.append(m.group(1) if m else nt)
            for k in keys:
                share[k] += c / max(1, len(keys))
                b = box.setdefault(k, [1e9, 1e9, -1e9, -1e9]); b[0] = min(b[0], x0); b[1] = min(b[1], y0); b[2] = max(b[2], x0); b[3] = max(b[3], y0)
    print(f'== {f}: {n} markers, sampled congestion {tot}')
    for k, v in share.most_common(12):
        b = box[k]; print(f'  {k:24s} {v:10.0f} {100*v/max(1,tot):5.1f}%  x {b[0]:.0f}-{b[2]:.0f} y {b[1]:.0f}-{b[3]:.0f}')
