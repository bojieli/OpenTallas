#!/usr/bin/env python3
"""Minimal real-waypoint clock vehicle for one actual pair of planned taps.

The vehicle replaces only the local clock branch for a mechanism experiment;
no full-die qualification or frozen-plan adoption is implied.
"""
import argparse
import json
import math
from pathlib import Path
import die_clock as DC
import schema as S


def midpoint(a,b,total,sign):
    axis=0 if abs(b[0]-a[0])>=abs(b[1]-a[1]) else 1
    cross=1-axis
    d=abs(b[0]-a[0])+abs(b[1]-a[1])
    if total+1e-6<d:raise ValueError('target shorter than physical endpoints')
    direction=1 if b[axis]>=a[axis] else -1
    v=max(a[cross],b[cross])+(total-d)/2 if sign>0 else min(a[cross],b[cross])-(total-d)/2
    # Equal L1 distance from each endpoint to the real intermediate buffer.
    u=(a[axis]+b[axis]+direction*sign*(a[cross]-b[cross]))/2
    out=[0.,0.];out[axis]=u;out[cross]=v
    return tuple(out)


def make(plan,source,ports,out):
    P=S.Plan(S.load(plan));out.mkdir(parents=True,exist_ok=True)
    original=json.loads((source/'tree.json').read_text())
    selected=[next(t for t in original['taps'] if t['port']==p) for p in ports]
    # The actual lowest common source in the inherited tree.
    prefix=[]
    for a,b in zip(selected[0]['path'],selected[1]['path']):
        if a!=b:break
        prefix.append(a)
    if not prefix:raise ValueError('pair has no common physical source')
    cells=json.loads((source/'place.json').read_text());common=prefix[-1]
    a=(cells[common]['x'],cells[common]['y'])
    K=DC.KeepIndex(DC.keepouts(P),die=(P.W,P.H))
    def free(p):
        return all(not K.hit(x,y) for x,y in [(p[0],p[1]),(p[0]+1.62,p[1]),(p[0],p[1]+.27),(p[0]+1.62,p[1]+.27)])
    start=max(sum(abs(x-y) for x,y in zip(a,t['xy'])) for t in selected)
    chosen=None
    for total in [math.ceil((start+32)/8.64)*8.64+i*8.64 for i in range(70)]:
        options=[]
        for t in selected:
            valid=[midpoint(a,t['xy'],total,s) for s in [1,-1]]
            valid=[q for q in valid if free(q)]
            if not valid:break
            options.append(valid[0])
        if len(options)==2 and total/2<=450:
            chosen=total,options;break
    if chosen is None:raise ValueError('no two-stage physical branch fits keepouts and <=450um legs')
    total,points=chosen
    T=DC.Tree();T.ports=[('input','root')]+[('output',t['port']) for t in selected]
    T.cell('nroot',*a,'node',9)
    T.nets=[dict(name='root',drv='port:root',branches=[(0.0,'M8','nroot',0.0)],routes=[[a,a]])]
    branches=[];routes=[];taps=[]
    for i,(t,p) in enumerate(zip(selected,points)):
        name=f'n_pair{i}';T.cell(name,*p,'node',10)
        actual=(T.cells[name]['x'],T.cells[name]['y'])
        def leg(s,d,load):
            g=sum(abs(x-y) for x,y in zip(s,d));return (g,'M8',load,g),[s,(d[0],s[1]),d]
        first,route=leg(a,actual,name);branches.append(first);routes.append(route)
        last,route=leg(actual,t['xy'],'port:'+t['port'])
        T.nets.append(dict(name=t['port'],drv=name,branches=[last],routes=[route]))
        taps.append({**t,'leaf':'nroot','path':['nroot',name],'pad_nets':[[t['port'],0]]})
    T.nets.append(dict(name='w_root',drv='nroot',branches=branches,routes=routes))
    DC.NDR_MODE='4w';DC.WIDE_LEVELS=0
    DC.write_verilog(T,out/'ctree.v');DC.write_spef(T,out/'ctree.spef')
    meta=dict(root_um=list(a),source_common=common,ports=ports,taps=2,cells=3,levels=2,
        leaf_um=1000,rep_um=450,buffer=DC.BUF,ndr='4W actual branches',core_early='off',
        wire_um=sum(L for n in T.nets for L,*_ in n['branches']),padding_um=0.,
        physical_pair=dict(target_branch_um=total,clock_stages_per_tap=2,maximum_leg_um=max(L for n in T.nets for L,*_ in n['branches']),
            data_cycles_added=0,clock_cell_area_um2=3*1.62*.27,keepout_hits=0,scope='pair mechanism only'))
    tree=dict(meta=meta,taps=taps,nodes={'nroot':dict(level=9,xy=list(a),kids=[],path=['nroot'])},root_node='nroot')
    (out/'tree.json').write_text(json.dumps(tree));(out/'place.json').write_text(json.dumps(T.cells))
    (out/'nets.json').write_text(json.dumps(dict(ports=T.ports,nets=T.nets)))
    return meta

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('plan',type=Path);ap.add_argument('source',type=Path)
    ap.add_argument('--ports',nargs=2,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();print(json.dumps(make(a.plan,a.source,a.ports,a.out),indent=2))
