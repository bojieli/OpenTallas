#!/usr/bin/env python3
"""KV-P2 10-23: census coverage (COORD G1 rule after the QC v2 62.9k-bit drop): as-built inter-partition bits vs the
bits the plan delivers.  Key = (src block, src port, dst partition); as-built bits = union of source bit indices over
every edge to a block in that partition; planned bits = the tree destination width (trees) or the gather-chain width
(gathers) for that key.  Clock / reset edges are listed by class and source port (spine/sync replacement must be
explicit, nothing silent).  The die_plan.json ports are also summed per lane to check the stage-1 -> plan emit.
usage: coverage_v31.py STAGE1 ASBUILT PLAN > coverage_v31.json"""
import collections, gzip, json, re, sys
sys.path.insert(0, __import__('os').path.dirname(__file__) or '.')
import plan_v31 as pv
import build_plan as v1

S = json.load(gzip.open(sys.argv[1]))
asb = json.load(gzip.open(sys.argv[2]))
plan = json.load(open(sys.argv[3]))
B, _ = pv.rewrite_asbuilt(asb)
where = {k: tuple(v) for k, v in S['where'].items()}
need = collections.defaultdict(set)
spine = collections.Counter()
for e in asb['edges']:
    ps, pd = where[e['s']][0], where[e['d']][0]
    if ps == pd:
        continue
    if v1.CLOCK_PORT.match(e['sp']):     # v3.1: by the SOURCE port (pll.locked -> host pll_locked is data)
        spine[('clock', e['s'], e['sp'])] += e['bits']
        continue
    if v1.RESET_PORT.search(e['dp']) and (e['sp'] in pv.SPINE_RESETS or e['sp'] in ('b', 'q')):
        spine[('reset', e['s'], e['sp'])] += e['bits']
        continue
    for a, b in e['sbits']:
        need[(e['s'], e['sp'], pd)].update(range(a, b + 1))
have = collections.Counter()
for t in S['trees']:
    for pd, n in t['dests'].items():
        have[(t['src'], t['sp'], pd)] = max(have[(t['src'], t['sp'], pd)], n)
gat = {(g['dst'], g['dp']): g for g in S['gathers']}
gdel = collections.Counter()
for e in asb['edges']:
    g = gat.get((e['d'], e['dp']))
    if g and where[e['s']][0] != g['dpart']:
        gdel[(e['s'], e['sp'], g['dpart'])] = 1
# narrow port families (plan_v3: width <= 64 -> one tree per re.sub(r'\d+', '#', port), member bits offset by 4096)
famtrees = {(t['src'], t['sp']) for t in S['trees'] if '#' in t['sp']}
fneed = collections.defaultdict(set)
for (s_, sp, pd), v in list(need.items()):
    f = re.sub(r'\d+', '#', sp)
    if (s_, f) in famtrees and (s_, sp) not in {(t['src'], t['sp']) for t in S['trees'] if t['src'] == s_}:
        fneed[(s_, f, pd)].update((sp, b) for b in v)
        del need[(s_, sp, pd)]
for k, v in fneed.items():
    need[k] = v
asb_bits = sum(len(v) for v in need.values())
dropped, short = [], 0
for k, v in need.items():
    if k in gdel:
        continue
    h = have.get(k, 0)
    if h < len(v):
        dropped.append(dict(src=k[0], sp=k[1], dst_part=k[2], asbuilt=len(v), planned=h))
        short += len(v) - h
gather_bits = sum(len(need[k]) for k in gdel if k in need)
plan_port_bits = sum(p['width'] for p in plan['ports'])
first_hop = collections.Counter()
for l in plan['lanes']:
    first_hop['lanes'] += 1
by_src = collections.Counter()
for (c, s, sp), n in spine.items():
    by_src[(c, B[s]['m'], sp)] += n
out = dict(asbuilt_interpartition_bits=asb_bits, planned_tree_bits=sum(min(have.get(k, 0), len(v)) for k, v in need.items() if k not in gdel),
           gather_chain_bits=gather_bits, dropped_bits=short, dropped=sorted(dropped, key=lambda d: -d['asbuilt'])[:50],
           n_dropped_keys=len(dropped),
           spine_replaced={f'{c} {m}.{sp}': n for (c, m, sp), n in sorted(by_src.items(), key=lambda kv: -kv[1])},
           spine_bits=dict(collections.Counter({c: n for (c, _, _), n in spine.items()}) if False else
                           {c: sum(n for (cc, _, _), n in spine.items() if cc == c) for c in ('clock', 'reset')}),
           plan_ports=len(plan['ports']), plan_port_bits_all_hops=plan_port_bits)
print(json.dumps(out, indent=1))
