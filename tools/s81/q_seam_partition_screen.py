#!/usr/bin/env python3
"""S81 Q element seam screen: count the actual crossing wires of the exact pre-memory-map Q source graph for the per-mac
partition (mac0 = g_mac[0] return + its hardened lane + its ROMs; mac1 = mirror; ctl = the rest), the same cell ownership rule as
tools/s81/q_native_partition_graph.py (MEMID / name / single-mac output alias).  usage: q_seam_partition_screen.py <source_graph.json.gz>"""
import json,gzip,sys,re,collections
d=json.load(gzip.open(sys.argv[1])); top='ot_v41_rom_elem_q_qxpq_w10'; m=d['modules'][top]
aliases=collections.defaultdict(set)
for n,net in m['netnames'].items():
    if not net.get('hide_name'):
        for b in net['bits']:
            if isinstance(b,int): aliases[b].add(n)
def macid(name):
    r=re.search(r'g_mac\[([01])\]',name); return r[1] if r else None
assign={}
for n,c in m['cells'].items():
    if 'MEMID' in c.get('parameters',{}): k=macid(c['parameters']['MEMID'])
    else: k=macid(n)
    if k is None:
        ids=set()
        for p,bits in c['connections'].items():
            if c['port_directions'].get(p)=='output':
                for b in bits:
                    for a in aliases.get(b,()): ids.update(re.findall(r'g_mac\[([01])\]',a))
        k=next(iter(ids)) if len(ids)==1 else None
    assign[n]='mac'+k if k else 'ctl'
clk={b for c in m['cells'].values() for p,bits in c['connections'].items() if p in('CLK','RD_CLK','WR_CLK') for b in bits if isinstance(b,int)}
users=collections.defaultdict(set); drv=collections.defaultdict(set)
for n,c in m['cells'].items():
    g=assign[n]
    for p,bits in c['connections'].items():
        for b in bits:
            if isinstance(b,int):
                users[b].add(g)
                if c['port_directions'].get(p) in('output','inout'): drv[b].add(g)
for p in m['ports'].values():
    for b in p['bits']:
        if isinstance(b,int): users[b].add('ext')
print('cells per group',collections.Counter(assign.values()))
pair=collections.Counter(); clkx=collections.Counter()
for b,u in users.items():
    gs=tuple(sorted(u-{'ext'}))
    if len(gs)>1:
        (clkx if b in clk else pair)[gs]+=1
print('crossing data bits by group set', pair.most_common())
print('clock bits crossing', clkx.most_common())
# FF counts per group
ff=collections.Counter()
for n,c in m['cells'].items():
    if 'DFF' in c['type'] or c['type'].startswith('$') and 'dff' in c['type'].lower(): ff[assign[n]]+=1
    if 'lane_pair' in c['type']: ff[assign[n]+'_lane']+=1
print('ff-ish',ff)
