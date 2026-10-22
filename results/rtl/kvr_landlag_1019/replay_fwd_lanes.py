#!/usr/bin/env python3
"""KVR-LANDLAG: rebuild RUN/fwd_lanes.json of a prep that failed at the lane-stations reach gate (kv_fwd_lanes.main raised
after writing case_kv/die.v but before fwd_lanes.json).  Replays kv_fwd_lanes.form on case_kv/die.v.prefwd (= the replica
netlist + the inserted stations) with the slots of rly_std.json + the moved landings of lane_stations.json, adds the
post-landing stages and plain added stages exactly as kv_fwd_lanes.iterate, and checks render() == case_kv/die.v."""
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
same = '\n'.join(FL.render(lines0, F)) == (case / 'die.v').read_text()
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
F['rep']['replay'] = dict(tool='scratch replay_fwd_lanes.py (KVR-LANDLAG)', render_equals_die_v=same,
                          note='prep FAILED at the lane reach gate before writing fwd_lanes.json; rows rebuilt by kv_fwd_lanes.form')
out.write_text(json.dumps(F['rep'], indent=1) + '\n')
print('REPLAY render==die.v', same, 'lanes', len(F['rep']['lanes']), 'totals', F['rep']['totals'],
      'plain', F['rep']['plain_added_stages'], 'post', sum(1 for L in F['rep']['lanes'] if L.get('post_stages')))
