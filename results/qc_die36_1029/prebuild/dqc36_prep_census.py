#!/usr/bin/env python3
"""DIE-QC-36: shift the moved clock cells (old tree -> legal re-sited tree) in a PG-access census input dir:
geometry.json cells bbox + ck_* signal_shapes, power_terms.json ck_* shapes. Everything else copied unchanged."""
import json, sys, shutil
from pathlib import Path
src, dst, old_t, new_t = map(Path, sys.argv[1:5]); dst.mkdir(parents=True, exist_ok=True)
old = json.load(open(old_t))['sites']; new = json.load(open(new_t))['sites']
dx = {'ck_'+k: round((new[k][0]-old[k][0])*1000) for k in new if abs(new[k][0]-old[k][0]) > 1e-9}
g = json.load(open(src/'geometry.json')); n = [0, 0, 0]
for c in g['cells']:
    d = dx.get(c['inst'])
    if d: b = c['bbox_dbu']; b[0] += d; b[2] += d; n[0] += 1
for r in g['signal_shapes']:
    d = dx.get(r[0])
    if d: r[3] += d; r[5] += d; n[1] += 1
g.setdefault('source', {}); g['dqc36_resite'] = dict(moved_cells=len(dx), cells_shifted=n[0], signal_shapes_shifted=n[1])
json.dump(g, open(dst/'geometry.json', 'w'), separators=(',', ':')); del g
t = json.load(open(src/'power_terms.json'))
for term in t['terms']:
    d = dx.get(term['inst'])
    if d:
        for s in term['shapes_dbu']: s[1] += d; s[3] += d
        n[2] += 1
json.dump(t, open(dst/'power_terms.json', 'w'), separators=(',', ':'))
for f in src.iterdir():
    if f.name not in ('geometry.json', 'power_terms.json'): shutil.copy(f, dst/f.name)
print(dict(moved=len(dx), cells_shifted=n[0], signal_shapes_shifted=n[1], power_terms_shifted=n[2]))
