#!/usr/bin/env python3
"""Nominal-frame cycles per ring from an add_lat.py run, against the sidecar and plan.

  read_lat.py PACKET PROFILE_TT PROFILE_FF SIDECAR PLAN OUT.json
"""
import collections
import json
import re
import sys
from pathlib import Path

packet, tt, ff, side, plan, out = sys.argv[1:7]
packet = Path(packet)
phase = dict(TT=json.load(open(tt))['phase'], FF=json.load(open(ff))['phase'])
side = json.load(open(side))
plan = json.load(open(plan))
sched = side['count_aligned']['ports']
added = {r['port']: r for r in side['ports']}
ports = {(p['dst']['part'], p['dst']['bus']): p for p in plan['ports']}
LINE = re.compile(r'^LAT (\S+) ready(\d+) fault(\d+) n(\d+) t0 ([\d.]+) v (\d+) tr ([\d.]+)')
T = 833.0
rows = {}
for corner in ('TT', 'FF'):
    ph = phase[corner]
    for line in (packet / f'{corner}.log').read_text().splitlines():
        m = LINE.match(line)
        if not m:
            continue
        label, ready, fault, n, t0, v, tr = m[1], int(m[2]), int(m[3]), int(m[4]), float(m[5]), int(m[6]), float(m[7])
        part, bus = label.split('__', 1)
        p = ports[(part, bus)]
        row = rows.setdefault(label, dict(port=p['id'], lane=added[p['id']]['lane'], src=p['src']['part'], dst=part,
                                          added=added[p['id']]['added_cycles'], sched_lat=sched[p['id']]['sched_lat'],
                                          K=sched[p['id']]['K']))
        c = dict(ready=ready, fault=fault, n=n)
        if ready and not fault and n:
            # Times in ns. Word v was launched at t0 + (v-1) periods on the sender clock.
            launch = t0 * 1000 + (v - 1) * T - ph['pc_' + p['src']['part']]['rise_ps']
            capture = tr * 1000 - ph['pc_' + part]['rise_ps']
            cycles = (capture - launch) / T
            c.update(cycles_exact=round(cycles, 4), cycles=round(cycles))
        row[corner] = c
tab = collections.Counter()
for r in rows.values():
    for corner in ('TT', 'FF'):
        c = r.get(corner, {})
        tab[(corner, r['added'], r['sched_lat'], c.get('cycles'))] += 1
frac = sorted({abs(c['cycles_exact'] - c['cycles']) for r in rows.values() for c in (r.get('TT', {}), r.get('FF', {})) if 'cycles' in c})
summary = dict(rings=len(rows), max_fraction=frac[-1] if frac else None,
               table=[dict(corner=k[0], added=k[1], sched_lat=k[2], measured=k[3], rings=v)
                      for k, v in sorted(tab.items(), key=str)],
               faulted={c: sorted(l for l, r in rows.items() if r.get(c, {}).get('fault') or not r.get(c, {}).get('ready')) for c in ('TT', 'FF')},
               rings_detail=rows)
Path(out).write_text(json.dumps(summary, indent=1) + '\n')
print(json.dumps({k: v for k, v in summary.items() if k != 'rings_detail'}, indent=0))
