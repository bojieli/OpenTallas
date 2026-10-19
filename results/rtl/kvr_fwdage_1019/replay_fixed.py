#!/usr/bin/env python3
"""KVR-FWDAGE 10-19: replay the kvs14r base lanes with the FIXED KV GEN (kv_fwd_lanes strap_k / landed_cost) -- KVR-LANDLAG's
replay method (results/rtl/kvr_landlag_1019/replay_fwd_lanes.py: kv_fwd_lanes.form on case_kv/die.v.prefwd + rly_std slots +
moved landings + post / plain added stages exactly as kv_fwd_lanes.iterate) -- and render the die.v the fixed GEN writes.
Checks: the fixed render differs from the base case_kv/die.v ONLY in landing K-strap pins (k0..k2 tie choice).
    replay_fixed.py SRC RUN OUTDIR    -> OUTDIR/fwd_lanes.json, OUTDIR/die.v, OUTDIR/replay.json"""
import json, re, sys
from collections import defaultdict
from pathlib import Path
src, run, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
sys.path.insert(0, str(src / 'tools/qwen_kv_die'))
import kv_fwd_lanes as FL
import kv_static_ages as KSA
case = run / 'case_kv'
lines0 = (case / 'die.v.prefwd').read_text().split('\n')
dirs, cur, pin = defaultdict(dict), None, None
for ln in (case / 'elements.lef.prefwd').read_text().split('\n'):
    s = ln.strip()
    if s.startswith('MACRO '):
        cur, pin = s.split()[1], None
    elif cur and s.startswith('PIN '):
        pin = s.split()[1]
    elif cur and pin and s.startswith('DIRECTION'):
        dirs[cur][pin] = s.split()[1].rstrip(';').upper()
slots = dict(json.loads((run / 'rly_std.json').read_text()).get('land_slots', {}))
st = json.loads((run / 'lane_stations.json').read_text())
for r in st['stations']:
    if r['op'] == 'slot':
        slots[r['inst']] = dict(source='kv_lane_stations', master=r['master'], x_um=r['x_um'], y_um=r['y_um'])
F = FL.form(lines0, dirs, slots)
new_v = '\n'.join(FL.render(lines0, F))
base = (case / 'die.v').read_text().split('\n')
nv = new_v.split('\n')
diff = [(a, b) for a, b in zip(base, nv) if a != b]
strip = lambda t: re.sub(r'\.k[012]\([^()]*\)', '.kX()', t)
only_straps = len(base) == len(nv) and all(strip(a) == strip(b) for a, b in diff)
inserted = {r['inst'] for r in st['stations'] if r['op'] in ('before', 'after')}
post = {r['of']: 1 for r in st['stations'] if r['op'] == 'after'}
for L in F['rep']['lanes']:
    L['inserted_stations'] = [c for c in L['stations'] if c in inserted]
    p = post.get(L['stations'][-1], 0)
    if p:
        L['post_stages'] = p; L['today'] += p; L['landed'] += p
in_lane = {c for L in F['rep']['lanes'] for c in L['stations']}
pos = defaultdict(set)
for r in st['stations']:
    if r['op'] == 'before' and r['inst'] not in in_lane:
        pos[KSA.lane_bid(r['of'])].add(re.sub(r'__s\d+$', '', r['of']))
F['rep']['plain_added_stages'] = {b: len(v) for b, v in sorted(pos.items())}
F['rep']['stations'] = st['summary']
F['rep']['replay'] = dict(tool='results/rtl/kvr_fwdage_1019/replay_fixed.py (KVR-FWDAGE)', changed_lines=len(diff),
                          changed_only_k_straps=only_straps)
out.mkdir(parents=True, exist_ok=True)
(out / 'fwd_lanes.json').write_text(json.dumps(F['rep'], indent=1) + '\n')
(out / 'die.v').write_text(new_v)
rec = dict(lanes=len(F['rep']['lanes']), changed_lines=len(diff), changed_only_k_straps=only_straps,
           changed_landings=sorted({re.match(r'\s*\S+ (\S+)', a).group(1) for a, _ in diff}))
(out / 'replay.json').write_text(json.dumps(rec, indent=1) + '\n')
print('REPLAY_FIXED lanes', rec['lanes'], 'changed lines', len(diff), 'only K straps', only_straps)
assert only_straps
