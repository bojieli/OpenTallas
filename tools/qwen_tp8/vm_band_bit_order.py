#!/usr/bin/env python3
"""Preserve logical lane-bit order while permuting eight physical pins locally."""
import collections,json
from pathlib import Path
import numpy as np
from scipy.optimize import linear_sum_assignment
from vm_lef_pins import read
from vm_band_pair import reach
ROOT=Path(__file__).resolve().parents[2]


def main():
    comp=json.loads((ROOT/'results/arch/qwen_tp8_1012/vm_band_composition_codex.json').read_text());x0,y0=comp['origin_um']
    ch={(c['bay'],c['slot']):c for c in comp['children'] if 'bay' in c}
    cols={int(c['inst'][3:]):c for c in comp['children'] if c['inst'].startswith('u_c')}
    pins={v:read(next((ROOT/v).glob('*.lef')))[1] for v in {c['view'] for c in ch.values()}}
    old=read(ROOT/'physical/ref_tile/qfd_vm_xcol_t/views/ot_qfd_vm_xcol_t/ot_qfd_vm_xcol_t.lef')[1]
    nodes=[];edges=[];adj=collections.defaultdict(set)
    for s in comp['segments']:
        prev=None
        for st in s['path']:
            i=len(nodes);nodes.append(st)
            if prev is not None:e=len(edges);edges.append((prev,i,None));adj[prev].add(e);adj[i].add(e)
            prev=i
        col=int(s['output'][0].split('_')[0][3:]);c=cols[col];port='d_hi' if s['output'][0].endswith('hi') else 'd_lo'
        fixed=[]
        for bit in range(8):p=old[f'{port}[{s["output"][1]+bit}]'];fixed.append((x0+c['at'][0]+p['x'],y0+c['at'][1]+p['y']))
        e=len(edges);edges.append((prev,None,fixed));adj[prev].add(e)
    orders=[n['bit_permutation'] for n in nodes]
    def point(i,port,bit,override):
        st=nodes[i];c=ch[st['bay'],st['slot']];physical=st['bit0']+override.get((i,bit),orders[i][bit]);p=pins[c['view']][f'{port}[{physical}]']
        return x0+c['at'][0]+p['x'],y0+c['at'][1]+p['y'],physical,c['view']
    def metric(e,bit,override=None):
        override=override or {};a,b,f=edges[e];ax,ay,ap,av=point(a,'q',bit,override)
        if b is None:bx,by=f[bit];h=500
        else:bx,by,bp,bv=point(b,'d',bit,override);h=reach(av,ap,bv,bp)
        d=abs(ax-bx)+abs(ay-by)
        return d,h
    def cost(e,bit,ov=None):
        d,h=metric(e,bit,ov);return 10000*max(0,d-h+.2)**2+d
    def stats():
        ds=[metric(e,b) for e in range(len(edges)) for b in range(8)]
        return dict(pair_failed_bits=sum(d>h for d,h in ds),max_um=round(max(d for d,h in ds),4))
    before=stats();history=[]
    for iteration in range(16):
        bad={i for e in range(len(edges)) if any(d>h-.2 for d,h in [metric(e,b) for b in range(8)]) for i in edges[e][:2] if i is not None};moves=0
        for i in bad:
            matrix=np.array([[sum(cost(e,bit,{(i,bit):physical}) for e in adj[i]) for physical in range(8)] for bit in range(8)])
            r,c=linear_sum_assignment(matrix);new=list(orders[i])
            for a,b in zip(r,c):new[int(a)]=int(b)
            old=sum(cost(e,bit) for e in adj[i] for bit in range(8));proposal={(i,b):new[b] for b in range(8)}
            value=sum(cost(e,b,proposal) for e in adj[i] for b in range(8))
            if value<old-1e-6:orders[i]=new;moves+=1
        state=dict(iteration=iteration,moves=moves,**stats());history.append(state);print(state,flush=True)
        if not moves:break
    rec=dict(schema='opentallas.qwen.vm-band-pin-bit-order.v1',before=before,after=stats(),rounds=history,
        physical_bit_permutations={st['placement_id']:orders[i] for i,st in enumerate(nodes) if orders[i]!=list(range(8))},
        structural_change='local8pinpermutations with exact logicalbit unpack; sameallstages andtileinstances')
    (ROOT/'results/arch/qwen_tp8_1012/vm_band_bit_order_codex.json').write_text(json.dumps(rec,indent=1)+'\n')


if __name__=='__main__':main()
