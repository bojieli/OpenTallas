#!/usr/bin/env python3
"""G1 census coverage for HBM plan v2: every as-built (r18h5 census) inter-partition bit vs the planned lanes.

Classes per census group (src inst.bus -> dst inst):
  internal   both ends map to one partition (no plan lane needed)
  covered    a planned lane from where[src] carries src.bus to where[dst] with >= as-built bits
  narrowed   covered, but with fewer planned bits (only the VM ring, 2224 -> --vm-ring-bits, is allowed)
  localised  a cross-quadrant as-built edge re-targeted to the same-quadrant copy of the destination role
  rerooted   obs status chain re-rooted at the C0 die-level root (per-quadrant port)
  dropped    none of the above (must be 0 except clock/reset)
Also checks that every census/block instance maps to a partition.
"""
import argparse, collections, gzip, json, re

ap = argparse.ArgumentParser()
ap.add_argument('--census', default='/srv/opentallas-scratch/claude/ft-tool/census/hbm_census.json.gz')
ap.add_argument('--out', required=True)
ap.add_argument('--blocks', default='/srv/opentallas-scratch/claude/ft-tool/dumps/dump-hbm/blocks.tsv')
a = ap.parse_args()
cen = json.load(gzip.open(a.census))
asg = json.load(open(f'{a.out}/v2_assign.json'))
# one SM macro spans its 4 stacked partitions <q>_sm<k>a..d (SPLIT_OF): coverage counts the SM as one unit
where = {i: re.sub(r'(_sm\d)[abcd]$', r'\1', p) for i, p in asg['where'].items()}
lanes = json.load(gzip.open(f'{a.out}/lane_members.json.gz'))


def norm(net):
    """plan net name -> as-built: die-level roots drive one registered output per quadrant (<bus>_q<Q>), the
    VM / COLL ring ports are named by neighbour axis (ring_h / ring_v) instead of cw / ccw."""
    i, b = net.split('.', 1)
    b = re.sub(r'_q(NW|NE|SW|SE)$', '', b)
    b = re.sub(r'(^|_)(c?cw|ring_[hv])(_|$)', r'\1RING\3', b)
    return f'{i}.{b}'


by_net = collections.defaultdict(list)
for lid, l in lanes.items():
    l['src'] = re.sub(r'(_sm\d)[abcd]$', r'\1', l['src'])
    l['dsts'] = [re.sub(r'(_sm\d)[abcd]$', r'\1', x) for x in l['dsts']]
    for n in l['nets']:
        by_net[norm(n)].append(l)

Q = re.compile(r'(NW|NE|SW|SE)')
cls = collections.Counter(); cbits = collections.Counter(); ex = collections.defaultdict(list)
unmapped = set()
for g in cen['groups']:
    s, d, b, k = g['src'], g['dst'], g['bits'], g['kind']
    if s not in where or d not in where:
        unmapped.update(x for x in (s, d) if x not in where)
        c = 'unmapped'
    else:
        ps, pd = where[s], where[d]
        net = norm(f"{s}.{g['src_bus']}")
        if ps == pd:
            c = 'internal'
        else:
            L = [l for l in by_net.get(net, []) if l['src'] == ps]
            hit = [l for l in L if pd in l['dsts']]
            if hit:
                pb = max(l['bits'] for l in hit)
                c = 'covered' if pb >= b or len(hit) > 1 and sum(l['bits'] for l in hit) >= b else 'narrowed'
            elif L and ps[:2] != pd[:2] and any(ps[:2] == x[:2] and Q.sub('', x) == Q.sub('', pd) for l in L for x in l['dsts']):
                c = 'localised'
            elif L and re.match(r'obs_', s) and any('C0' in l['dsts'] for l in L):
                c = 'rerooted'            # obs status chain: per-quadrant port into the C0 root instead of NE->NW->...
            elif L:
                c = 'retargeted'
            else:
                c = 'dropped'
    if c == 'dropped' and k in ('clock', 'reset'):
        c = 'dropped_clkrst'
    cls[c] += 1; cbits[c] += b
    if len(ex[c]) < 12:
        ex[c].append(f"{g['src']}.{g['src_bus']}->{g['dst']} {b}b {k}")
inter = sum(v for c, v in cbits.items() if c != 'internal')
# every placed block of the as-built die: relays / landing flops (hbfd_*, rf*, rfr_*, hidxr_*) are replaced by the plan's
# ft-slot stations; every other block must map to a partition.  hb_ckgen (clock only, not in the census) = C0 spine root.
CLOCK_ONLY = {'hb_ckgen': 'C0'}
nblk = nrel = 0; blk_unmapped = []
for line in open(a.blocks):
    f = line.split('\t'); nblk += 1
    if f[1].startswith('hbfd_') or re.match(r'^(rf\d|rfr_|hidxr_)', f[0]):
        nrel += 1
    elif f[0] not in where and f[0] not in CLOCK_ONLY:
        blk_unmapped.append(f[0])
rep = dict(blocks=dict(total=nblk, relays_replaced_by_stations=nrel, mapped=nblk - nrel - len(blk_unmapped),
                       clock_only=CLOCK_ONLY, unmapped=blk_unmapped),groups=dict(cls), bits=dict(cbits), inter_partition_bits_as_built=inter,
           planned_lane_bits=sum(l['bits'] * len(l['dsts']) for l in lanes.values()),
           unmapped_instances=sorted(unmapped), examples=ex)
json.dump(rep, open(f'{a.out}/coverage.json', 'w'), indent=1)
print(json.dumps({k: rep[k] for k in ('groups', 'bits', 'inter_partition_bits_as_built', 'planned_lane_bits')}))
print('unmapped census instances', len(unmapped), sorted(unmapped)[:10], 'blocks', rep['blocks'])
for c in ('narrowed', 'localised', 'retargeted', 'dropped', 'dropped_clkrst', 'unmapped'):
    if ex.get(c):
        print(c, ex[c][:6])
