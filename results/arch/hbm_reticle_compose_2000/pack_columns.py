#!/usr/bin/env python3
"""One bounded composition of source-bound individual Col8 rectangles.

Each column keeps its measured relative geometry. An exclusive service envelope
protects its internal seams during this first attempt; it is not a hard macro or
an adopted quarter outline. All old score slots remain as conservative reserves
for the separately enumerated outside-column logic. Failure is not global no-fit.
"""
import hashlib
import json
import math
import time
from pathlib import Path

start = time.time()
D = json.loads(Path('input.json').read_text())
S = json.loads(Path('source_geometry.json').read_text())
C = json.loads(Path('column_geometry.json').read_text())
P = D['placement']
W, H = D['die_um']
GRID, CLEAR, TILE = 216.0, 21.6, 432.0
cw, ch = C['outline_um']
# Automatic relay bodies require regeneration, retained explicitly in the output.
auto = {n: p for n, p in P.items() if p['m'].startswith(
    ('hbfd_rly_', 'hbfd_land_', 'hbfd_lh_', 'hbfd_lh0_'))}
fixed = {n: p for n, p in P.items() if n not in auto and n != 'hc_eng'}
for i, b in enumerate(S['last_step_postcut_bands']):
    fixed['service_corridor_' + str(i)] = dict(
        x=b['start_um'] if b['axis'] == 'x' else 0,
        y=b['start_um'] if b['axis'] == 'y' else 0,
        w=b['width_um'] if b['axis'] == 'x' else W,
        h=b['width_um'] if b['axis'] == 'y' else H,
        m='SOURCE_INSERTION_BAND_RESERVE')

buckets = {}
def keys(a):
    for x in range(int((a['x']-CLEAR)//TILE), int((a['x']+a['w']+CLEAR)//TILE)+1):
        for y in range(int((a['y']-CLEAR)//TILE), int((a['y']+a['h']+CLEAR)//TILE)+1):
            yield x, y

def add(n, a):
    fixed[n] = a
    for k in keys(a):
        buckets.setdefault(k, set()).add(n)

def overlaps(a, b):
    return (a['x']-CLEAR < b['x']+b['w'] and b['x'] < a['x']+a['w']+CLEAR
            and a['y']-CLEAR < b['y']+b['h'] and b['y'] < a['y']+a['h']+CLEAR)

for n, a in list(fixed.items()):
    add(n, a)

def blocked(a):
    seen = set()
    for k in keys(a):
        for n in buckets.get(k, ()):
            if n not in seen:
                seen.add(n)
                if overlaps(a, fixed[n]):
                    return True
    return False

anchors = [(x*GRID, y*GRID)
           for x in range(1, int((W-cw)/GRID)+1)
           for y in range(1, int((H-ch)/GRID)+1)]
placed, failed, rectangles = {}, [], {}
targets = []
for q in ('SW', 'SE', 'NW', 'NE'):
    old = P['hb_idx__s_' + q]
    for e in range(2):
        for leaf in range(4):
            for col in range(4):
                targets.append((f'{q}.engine{e}.leaf{leaf}.column{col}', old))

# Keep the actual enlarged HC root, independently of all column replicas.
root = P['hc_eng']
todo = [('hc_eng', root, 907.2, 734.4)] + [(n, a, cw, ch) for n, a in targets]
for n, old, w, h in todo:
    chosen = None
    for x, y in sorted(anchors, key=lambda p: abs(p[0]-old['x'])+abs(p[1]-old['y'])):
        a = dict(x=x, y=y, w=w, h=h)
        if x+w <= W and y+h <= H and not blocked(a):
            chosen = a
            break
    if chosen is None:
        failed.append(n)
        continue
    placed[n] = chosen
    add('internal_service_envelope:' + n, chosen)
    if n != 'hc_eng':
        for r in C['rectangles']:
            rectangles[n + '/' + r['name']] = dict(
                r, x_um=round(chosen['x']+r['x_um'], 6),
                y_um=round(chosen['y']+r['y_um'], 6))

out = dict(
    status='BOUNDED_DIAGNOSTIC_COMPOSITION_COMPLETE' if not failed else
           'BOUNDED_SERVICE_ENVELOPE_ATTEMPT_INCOMPLETE_NOT_GLOBAL_NO_FIT',
    input_manifest_sha256=D['manifest_sha256'],
    column_geometry_sha256=hashlib.sha256(Path('column_geometry.json').read_bytes()).hexdigest(),
    die_um=[W, H], placed_service_envelopes=placed, unplaced=failed,
    individual_source_rectangles=rectangles,
    placed_columns=sum(n != 'hc_eng' for n in placed), required_columns=128,
    required_pairs=512, required_raw_seam_srams=1536,
    original_quarter_reserves=[n for n in P if n.startswith('hb_idx__s_')],
    automatic_relays_requiring_regeneration=auto,
    grid_um=GRID, clearance_um=CLEAR, runtime_s=time.time()-start,
    open=['Service envelopes are conservative placement constraints, not hard macros.',
          'Old quarter rectangles reserve all outside-column controls conservatively; native footprint remains open.',
          'R3 view, composed clocks/reset, actual routes and any additional die hops remain unqualified.',
          'No extra transport age is claimed beyond the source-proved +23.',
          'This single fixed-other-body attempt cannot establish global no-fit.'])
Path('columns_composition.json').write_text(json.dumps(out, indent=1)+'\n')
print(json.dumps({k: out[k] for k in ('status', 'placed_columns', 'required_columns', 'unplaced', 'runtime_s')}))
