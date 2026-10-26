#!/usr/bin/env python3
"""KV-P5 10-23: R8 input prep for the KV die (after r8_fault_exempt.py).  R8 (1) keeps the as-built relative offsets of
ONE as-built bus.  An offset between two source pins of one source leaf that is NOT the same in every instance of the sink
type was never a functional invariant (the same hardened leaf RTL ran with each value as built: the as-built die was
asymmetric, e.g. ectl cfg (kvs_hroot o_c5) vs kgo (o_kg) +4 in EN/ES and +1 in WN/WS) -> those pins are separate buses.
Pins whose pairwise as-built offsets are identical in every instance stay one bus.  Writes member field `bus_sub`
(r8.bus_key splits a leaf bus by it, claude/kv-p5-r8-1023).

    r8_invariant_split.py PLAN.json BUS_GROUPS_IN.json OUT.json
"""
import json
import re
import sys
from collections import defaultdict

Q = re.compile(r'_(EN|ES|WN|WS)(?=_|$|\.)')
plan = json.load(open(sys.argv[1]))
bg = json.load(open(sys.argv[2]))
ptype = {p['name']: p['type'] for p in plan['partitions']}
norm = lambda s: Q.sub('_Q', s)
# instance buses: (sink, src_part, src leaf) -> {pin key: asbuilt}
inst = defaultdict(dict)
for g in bg['landing']:
    for m in g['members']:
        if m.get('lane') == 'spine':
            continue
        leaf, _, pin = m['source'].rpartition('.')
        pk = (m['sink_port'], pin, json.dumps(m['sink_bits']))
        inst[(g['sink'], g['sink_part'], g['src_part'], leaf)][pk] = m['asbuilt_stages']
# type buses: (sink type, normalised sink, normalised src part, normalised leaf) -> [instance offset maps]
tb = defaultdict(list)
for (sink, sp, srcp, leaf), pins in inst.items():
    tb[(ptype.get(sp, sp), norm(sink), norm(srcp), norm(leaf))].append(pins)
sub = {}            # (type key, pin key) -> sub id
nsplit = 0
for tk, insts in tb.items():
    keys = sorted(set().union(*[set(p) for p in insts]))
    par = {k: k for k in keys}
    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            offs = {p[a] - p[b] for p in insts if a in p and b in p}
            if len(offs) == 1:
                par[find(a)] = find(b)
    roots = sorted({find(k) for k in keys})
    if len(roots) > 1:
        nsplit += 1
    for k in keys:
        sub[(tk, k)] = roots.index(find(k))
n = 0
for g in bg['landing']:
    for m in g['members']:
        if m.get('lane') == 'spine':
            continue
        leaf, _, pin = m['source'].rpartition('.')
        tk = (ptype.get(g['sink_part'], g['sink_part']), norm(g['sink']), norm(g['src_part']), norm(leaf))
        s = sub[(tk, (m['sink_port'], pin, json.dumps(m['sink_bits'])))]
        if s:
            m['bus_sub'] = s
            n += 1
bg['note'] = bg.get('note', '') + ' | KV-P5 r8_invariant_split: bus_sub on members whose as-built offset varies across the sink type'
json.dump(bg, open(sys.argv[3], 'w'))
print(f'{nsplit} type buses split, {n} members re-bused')
