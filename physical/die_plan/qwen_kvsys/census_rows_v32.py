#!/usr/bin/env python3
"""KV-P3 10-23: G0 census source for die_plan v3.2 (= census_rows_v31 on the plan_v32 view: relays are leaves, ID lanes, landing checks + fault chains; forward_via = the tap-tree forwarding partitions of the plan). v3.1 doc: (tools/die_plan/census_cov.py format).
Rows = as-built rtl6 inter-block connectivity after the plan_v31 rewrites (SerDes split, host cluster, astk relabel),
one row per (src block, src port, dst partition) with bits = UNION of source bits (a port fanning out to several
blocks of one partition is one set of wires), the destination instance being the first such block.
Gathers (PV result T-chain, 8 x 256+2 b into hub_C RH): the as-built transport is the qkd_rlyi_258s MUX relay chain
(bind/bitcon.py), so its rows are chain rows partition -> next partition (258 b per hop, the chain width), not
join -> RH (which would count 17 x 256 b of select-merged sources as separate wires).
    python3 census_rows_v32.py STAGE1 ASBUILT  -> census/census_rows_v32.tsv.gz + census/census_map_v32.json"""
import collections, gzip, json, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plan_v32  # noqa: F401  (v3.2 as-built view)
import plan_v31 as pv
import build_plan as v1

S = json.load(gzip.open(sys.argv[1])); asb = json.load(gzip.open(sys.argv[2]))
B, _ = pv.rewrite_asbuilt(asb)
where = {k: v[0] for k, v in S['where'].items()}
gat = {(g['dst'], g['dp']): g for g in S['gathers']}
need = collections.defaultdict(set); first = {}; kind = {}
for e in asb['edges']:
    ps, pd = where[e['s']], where[e['d']]
    if ps == pd or (e['d'], e['dp']) in gat:
        continue
    k = (e['s'], e['sp'], pd)
    if v1.CLOCK_PORT.match(e['sp']):
        kind[k] = 'clock'
    elif v1.RESET_PORT.search(e['dp']) and (e['sp'] in pv.SPINE_RESETS or e['sp'] in ('b', 'q')):
        kind[k] = 'reset'
    else:
        kind.setdefault(k, 'data')
    first.setdefault(k, (e['d'], e['dp']))
    for a, b in e['sbits']:
        need[k].update(range(a, b + 1))
rows = []
for k, v in need.items():
    d, dp = first[k]
    rows.append((k[0], k[1], d, dp, kind[k], len(v)))
for (dst, dp), g in gat.items():
    chain = g['srcparts'] + ([g['dpart']] if g['dpart'] not in g['srcparts'] else [])
    for a_, b_ in zip(chain, chain[1:]):
        rows.append((f'tchain:{dst}.{dp}@{a_}', 'b', f'tchain:{dst}.{dp}@{b_}' if b_ != g['dpart'] else dst,
                     'y' if b_ != g['dpart'] else dp, 'data', g['width']))
os.makedirs('census', exist_ok=True)
with gzip.open('census/census_rows_v32.tsv.gz', 'wt') as f:
    f.write('src\tsrc_bus\tdst\tdst_bus\tkind\tbits\n')
    for r in sorted(rows):
        f.write('\t'.join(map(str, r)) + '\n')
parts = dict(where)
for (dst, dp), g in gat.items():
    for p in g['srcparts']:
        parts[f'tchain:{dst}.{dp}@{p}'] = p
fwd = sorted({u for t in S['trees'] for (u, v, f, b) in t['edges'] if u != t['root']} |
             {v for t in S['trees'] for (u, v, f, b) in t['edges'] if v not in t['dests']})
json.dump(dict(parts=parts, forward_via=['^' + re.escape(x) + '$' for x in fwd],
               forward_routes=[{'src': 'host', 'src_bus': 'link_rst_n', 'dst': 'd2d_kv', 'dst_bus': 'rst_n', 'lanes': ['L745', 'L746']}, {'src': 'host', 'src_bus': 'link_rst_n', 'dst': 'serdes_E', 'dst_bus': 'rst_n', 'lanes': ['L745', 'L746', 'L747']}, {'src': 'serdes_E', 'src_bus': 'tx_up', 'dst': 'host', 'dst_bus': 'fdi', 'lanes': ['L2046', 'L2047']}, {'src': 'serdes_W', 'src_bus': 'tx_up', 'dst': 'host', 'dst_bus': 'fdi', 'lanes': ['L2049', 'L2051']}], exempt=[
    dict(match='^clock$', kind='clock', replaced_by='die clock spine (core) + v3.2 regional spines clk_hbm_WS/WN/ES/EN, clk_phy/host/ingest (hub_C -> hub_Wi), clk_fwd (hub_C -> sys_c): clocks_v32.json',
         reason='clock nets are not lanes'),
    dict(match='^reset$', kind='reset', replaced_by='die reset spine + per-partition sync',
         reason='host.die_rst_n / relay reset fan-out (5,760 b as built)')],
    note='as-built rtl6 e33504a6f after plan_v32 (relays as leaves, ID lanes, landing checks + fault chains)'),
    open('census/census_map_v32.json', 'w'), indent=0)
print('rows', len(rows), 'bits', sum(r[5] for r in rows), collections.Counter(r[4] for r in rows))
