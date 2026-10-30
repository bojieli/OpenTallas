#!/usr/bin/env python3
"""DIE-HBM-26 HBM-004: classify the 92 UNPLANNED pairs of d25b + g4 strict bind (82,285 b) by fix kind.
Inputs: plan die_plan.json, full-cap bind report (probe: unplanned_bit_list uncapped), lane_add report(s).
Classes (per pair, from the as-built drivers/sinks + the plan):
  WIDEN   the pair already has plan lanes that are full: as-built width > planned (census fold took max over the
          folded quadrants; the as-built half carries both quadrant instances).  Fix = widen the existing lanes
          (same stations/cycles -> 0 tok/s); needs face window capacity, not a new route.
  SPLIT   one source family (same top instance) crosses partitions that the map scattered: driver and sink are the
          same family (hb_idx__s_*, sfucore_*, su_*).  Fix = MAP/RE-HOME (12.13): co-locate the family (partition
          order or leaf regrouping), then ADJ lanes or none.
  REMAP   a plan lane with the same family/width exists but is UNUSED at another partition (map put the leaf
          elsewhere): fix = map the leaf where the plan lane is (or move the lane end).
  NEW     cross-family as-built link the plan never had: fix = plan lane add (hop chain <= 405 um per station) or
          re-home.
"""
import collections, json, re, sys
plan = json.load(open(sys.argv[1])); rep = json.load(open(sys.argv[2])); la = json.load(open(sys.argv[3]))
T = plan['partition_types']; P = {p['name']: p for p in plan['partitions']}
def rect(n):
    p = P[n]; w, h = T[p['type']]['outline_um']
    if p.get('orient', 'R0') in ('R90', 'R270', 'MXR90', 'MYR90'): w, h = h, w
    x, y = p['origin_um']; return (x, y, x + w, y + h)
def gap(a, b):
    A, B = rect(a), rect(b); return max(0, B[0] - A[2], A[0] - B[2]) + max(0, B[1] - A[3], A[1] - B[3])
ports = {p['id']: p for p in plan['ports']}
planned = collections.Counter()
for l in plan['lanes']:
    ps = [ports[i] for i in l['ports'] if i in ports]
    if ps: planned[(ps[0]['src']['part'], ps[-1]['dst']['part'])] += ps[0]['width']
L = rep['lanes']; up = L['unplanned_pairs']
fam = lambda s: re.sub(r'\[\d+\]', '', s.split('.')[0])
drv = collections.defaultdict(collections.Counter); snk = collections.defaultdict(collections.Counter)
for b in L['unplanned_bit_list']:
    k = (b['src_part'], b['dst_part']); drv[k][fam(b['driver'])] += 1
    for s in b['sink_ports'][:1]: snk[k][s.split('.')[0]] += 1
unused = {}
for l in plan['lanes']:
    if l['id'] in set(L['unused_examples']):
        ps = [ports[i] for i in l['ports']]; unused[l['id']] = (ps[0]['src']['part'], ps[-1]['dst']['part'], ps[0]['width'])
REMAP = {  # unplanned pair -> unused plan lane with the same family / width (plan end differs from the map)
    ('NE_b103', 'root'): 'L64m', ('NW_b103', 'root'): 'L64', ('root', 'NE_b000'): 'L80m', ('root', 'NW_b000'): 'L80',
    ('NE_b111', 'NE_hub'): 'L81m', ('NW_b111', 'NW_hub'): 'L81'}
lam = {}
for key in ('built', 'far', 'failed'):
    for r in la.get(key, []) if isinstance(la.get(key), list) else []:
        lam[(r['src'], r['dst'])] = key.upper() + (': ' + r['why'] if r.get('why') else '')
rows = []
for k, n in up.items():
    s, d = k.split('->'); key = (s, d)
    df = drv[key].most_common(1)[0][0] if drv[key] else '?'
    sf = snk[key].most_common(1)[0][0] if snk[key] else '?'
    sfam = re.sub(r'^u_|_Q.*$', '', sf)
    if planned[key] > 0: cls = 'WIDEN'
    elif key in REMAP: cls = 'REMAP'
    elif re.match(r'(hb_idx__s_|sfucore_|su_)', df) and (df.split('_')[-1] in sf or sf.startswith(('ge[', 'gc[', '$')) or
                                                         (df.startswith('sfucore') and 'sfucore' in sf) or (df.startswith('hb_idx__s_') and sf.startswith('u_hb_idx__s_')) or
                                                         (df.startswith('su_') and sf.startswith('u_su_'))):
        cls = 'SPLIT'
    else: cls = 'NEW'
    rows.append(dict(pair=k, bits=n, cls=cls, planned_bits=planned[key], gap_um=round(gap(s, d), 1), driver_family=df,
                     sink=sf, plan_lane=REMAP.get(key), lane_add_1200=lam.get(key, '')))
rows.sort(key=lambda r: (r['cls'], -r['bits']))
tot = collections.defaultdict(lambda: [0, 0])
for r in rows: tot[r['cls']][0] += 1; tot[r['cls']][1] += r['bits']
json.dump(dict(schema='opentallas.hbm.hbm004_classes.v1', pairs=len(rows), bits=sum(up.values()),
               classes={k: dict(pairs=v[0], bits=v[1]) for k, v in sorted(tot.items())}, rows=rows),
          open(sys.argv[4], 'w'), indent=1)
print(json.dumps({k: v for k, v in sorted(tot.items())}), sum(up.values()))
for r in rows: print(f"{r['cls']:6s} {r['pair']:22s} {r['bits']:5d} plan {r['planned_bits']:5d} gap {r['gap_um']:8.1f} {r['driver_family']:16s} -> {r['sink'][:28]:28s} {r['plan_lane'] or ''} {r['lane_add_1200'][:60]}")
