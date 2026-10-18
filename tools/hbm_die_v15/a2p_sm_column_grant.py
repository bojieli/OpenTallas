#!/usr/bin/env python3
"""A2P SM column grant (H-DIE 10-16): the H-SM F108 column pin file (opentallas.hbm.sm_column_pins.v1, per-bit exact
pins in the R0 frame) -> the sm_<q><i> slots of an A2P grant contract.  Per port one slot pin entry {name 'p[hi:lo]',
face, layer, offset, span_um} (span = first..last bit x of the port's run; the exact per-bit list stays in the pin file,
referenced by sha256); S-quadrant columns R0, N-quadrant columns MX (H-SM: legal, x unchanged, N<->S swapped);
clock_entry = the E-face clk pin (one regional root); reserved channels removed (no in-column feedthrough).
    a2p_sm_column_grant.py GRANTS PINFILE [--source-commit C]       (rewrites GRANTS)"""
import argparse, collections, hashlib, json
from pathlib import Path
ap = argparse.ArgumentParser(); ap.add_argument('grants'); ap.add_argument('pins'); ap.add_argument('--source-commit', default='')
a = ap.parse_args()
G = json.loads(Path(a.grants).read_text()); raw = Path(a.pins).read_bytes(); d = json.loads(raw)
W_, H_ = d['outline_um']
runs = collections.OrderedDict()
for p in d['pins']:
    k = (p['port'], p['face'])
    r = runs.setdefault(k, dict(bits=[], xs=[], ys=[], layers=set(), direction=p['direction']))
    r['bits'].append(p['bit']); r['xs'].append(p['x']); r['ys'].append(p['y']); r['layers'].add(p['layer'])
pins, clk = [], None
for (port, face), r in runs.items():
    hi, lo = max(r['bits']), min(r['bits'])
    along = r['xs'] if face in 'NS' else r['ys']
    s0, s1 = min(along), max(along)
    name = f'{port}[{hi}:{lo}]' if hi > 0 or len(r['bits']) > 1 else port
    pins.append(dict(name=name, face=face, layer='/'.join(sorted(r['layers'])), offset=round((s0 + s1) / 2, 3),
                     span_um=[round(s0, 3), round(s1, 3)], direction=r['direction'], offset_pending_view=False))
    if port == 'clk':
        clk = dict(pin='clk', face=face, layer=sorted(r['layers'])[0], offset=round(s0, 3))
n = 0
for s in G['slots']:
    if not s['name'].startswith('sm_'):
        continue
    assert abs(s['outline']['w'] - W_) < 1e-3 and abs(s['outline']['h'] - H_) < 1e-3, (s['name'], s['outline'], (W_, H_))
    q = s['name'][3:5]
    s['origin']['orient'] = 'MX' if q.startswith('N') else 'R0'
    s.update(pins=pins, pin_status='COLUMN_PIN_FILE_EXACT (H-SM F108 sm_column_pins.v1; frame kit LEF pending rp4h/i one-root view)',
             pin_file=dict(path=str(a.pins), sha256=hashlib.sha256(raw).hexdigest(), source_commit=a.source_commit,
                           frame=d.get('frame'), windows=d.get('windows')),
             reserved_channels=[], clock_entry=clk or s.get('clock_entry'), grant='a2p_sm_column_1016')
    n += 1
G.setdefault('a2p_sm_column_grant', []).append(dict(slots=n, pin_file=str(a.pins), source_commit=a.source_commit, ports=len(pins)))
Path(a.grants).write_text(json.dumps(G, indent=1) + '\n')
print(json.dumps(dict(slots=n, ports=len(pins), clock=clk, faces=collections.Counter(p['face'] for p in pins))))
