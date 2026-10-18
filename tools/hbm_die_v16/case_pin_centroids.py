#!/usr/bin/env python3
"""H-RELAY 1017: per (instance, port) placed pin centroid of every NON-relay block of a die case (manifest placement x
view LEF pin rectangles, case_reach transforms).  Input to relay_lanes_d4f.py (lane bundling checks the driver-pin ->
trunk-root and trunk-end -> sink-pin hops against the reach).
    case_pin_centroids.py CASE_DIR --out PINS.json.gz"""
import argparse, collections, gzip, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hbm_die_v15'))
import case_reach as CR  # noqa: E402

ap = argparse.ArgumentParser(); ap.add_argument('case', type=Path); ap.add_argument('--out', required=True)
a = ap.parse_args()
man = json.loads((a.case / 'manifest.json').read_text())
pl = {n: dict(v, orient=v.get('orient', v.get('o')), master=v.get('master', v.get('m'))) for n, v in man['placement'].items()}
want = {v['master'] for v in pl.values() if not v['master'].startswith('hbfd_rly')}
L = {}
for f in (a.case / 'views').glob('*.lef'):
    if f.stem in want or any(m in want for m in re.findall(r'^MACRO (\S+)', f.read_text()[:4000], re.M)):
        L.update(CR.lef(f))
out = {}
for n, v in pl.items():
    if v['master'].startswith('hbfd_rly') or v['master'] not in L:
        continue
    lv = L[v['master']]; acc = collections.defaultdict(lambda: [0.0, 0.0, 0])
    for pn, (px, py) in lv['pins'].items():
        if lv['uses'].get(pn) == 'CLOCK':
            continue
        b = re.sub(r'\[\d+\]$', '', pn); x, y = CR.xf(v, lv['w'], lv['h'], px, py)
        s = acc[b]; s[0] += x; s[1] += y; s[2] += 1
    out[n] = {p: [round(s[0] / s[2], 1), round(s[1] / s[2], 1), s[2]] for p, s in acc.items()}
with gzip.open(a.out, 'wt') as f:
    json.dump(dict(schema='opentallas.hbm.case_pin_centroids.v1', case=str(a.case), instances=out), f)
print('instances', len(out), 'ports', sum(len(v) for v in out.values()))
