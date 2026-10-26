#!/usr/bin/env python3
"""Recover a minimum tree arrival graph from geometry dumps; this is not a functional die netlist.
Port roles are inherited from a pinned actual netlist. Validate baseline equivalence
before using this to inspect a candidate; emit the generator's full netlist for adoption.
"""
import argparse, collections, json, re, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'qwen_die_seam'))
import extract, tree_alignment
p=argparse.ArgumentParser();p.add_argument('dump');p.add_argument('baseline_die');p.add_argument('out');a=p.parse_args()
d=json.load(open(a.dump));old,bs=extract.parse(a.baseline_die);I={i['n']:i for i in d['insts']};C=collections.defaultdict(dict);wires=[]
for bid,cls,bits,eps in d['buses']:
    base=re.sub(r'__r\d+$','',bid);b=bs.get('n_'+base)
    if not b or b['cls'] not in ('tree','corridor'):continue
    net='n_'+bid;wires.append(f'  wire [{bits-1}:0] {net};')
    for k,n in enumerate(eps):
        if I[n]['m'].startswith(('qfd_rly','qkd_rly')):port='b' if k==0 else 'a'
        else:
            src=[s.split('.',1)[1] for s in b['src'] if s.split('.',1)[0]==n]
            dst=[s.split('.',1)[1] for s in b['dst'] if s.split('.',1)[0]==n]
            roles=src if k==0 else dst
            if not roles:roles=dst if k==0 else src
            if len(roles)!=1:raise ValueError((bid,n,k,roles,b))
            port=roles[0]
        if port in C[n] and C[n][port]!=net:raise ValueError(('duplicate port',n,port,C[n][port],net))
        C[n][port]=net
text=['// STATIC TREE GRAPH ONLY; not functional RTL or a routed die','module qfd_die();']+wires
for n,pins in C.items():text.append('  '+I[n]['m']+' '+n+' ('+', '.join(f'.{k}({v})' for k,v in pins.items())+');')
text+=['endmodule'];Path(a.out).write_text('\n'.join(text)+'\n')
r=tree_alignment.audit(a.out);Path(a.out+'.audit.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k] for k in ('nodes','misaligned','proposed_pad_relays','relay_count')}))
