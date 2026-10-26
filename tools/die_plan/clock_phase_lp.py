#!/usr/bin/env python3
"""Measured two-corner clock phase targets within the available buffer-chain hull.

This is a CTS planning model, never timing sign-off. Variables are each tap's TT
and FF added delay. Each directed related-pair inequality includes measured min
and max arrivals and only the die-root CPPR range. The convex hull is measured
from the same stock-cell library chains used by the endpoint selector.
"""
import argparse
import itertools
import json
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
from scipy.spatial import ConvexHull
import scipy.sparse as sp
import die_clock_leaftrim as L
M=L.M


def run(a):
    base,prev=Path(a.dir),Path(a.calibration)
    mesh=json.loads((base/'mesh.json').read_text());old=json.loads((prev/'mesh.json').read_text())
    if Path(old['meta']['leaftrim']['source']).resolve()!=base.resolve():raise ValueError('wrong calibration baseline')
    plan=M.S.Plan(M.S.load(a.plan));cells=json.loads((prev/'place.json').read_text())
    byport={t['port']:t for t in mesh['taps']};ports=sorted(byport);idx={p:i for i,p in enumerate(ports)};N=len(ports)
    oldt={t['port']:t for t in old['taps']}
    offsets=M.DC.plan_tap_early(plan)
    def off(p,c):
        t=byport[p]
        return offsets.get((t['part'],t['tap']),{}).get(c,t.get('early_ps',0.0))
    arr={c:L.taps(base/f'taps_{c}.txt') for c in ('TT','FF')};cur={c:L.taps(prev/f'taps_{c}.txt') for c in ('TT','FF')}
    libs={c:L.lib_cells(c,a.libdir) for c in ('TT','FF')}
    opts=[f'BUFx{k}_ASAP7_75t_R' for k in a.family.split(',')]
    chains=[[M.BUF]+list(q)+[M.BUF] for n in range(a.min_cells-2,a.max_cells-1) for q in itertools.combinations_with_replacement(opts,n)]
    def ds(ch,c):return L.chain_delay(libs[c],ch,40.,3.,wire_ff=4.)[0]
    pts=np.array([[ds(ch,'TT'),ds(ch,'FF')] for ch in chains]);hull=ConvexHull(pts)
    latebias={c:{} for c in ('TT','FF')};earlybias={c:{} for c in ('TT','FF')};credit={}
    for c in ('TT','FF'):
        _,tree=M.read_tree(prev/f'tree_{c}.txt');credit[c]=tree['ckm_n0'][0]-tree['ckm_n0'][1]
        for p in ports:
            ch=[cells[n].get('lib',M.BUF) for n in oldt[p]['leaftrim']['cells']];nom=ds(ch,c)
            latebias[c][p]=cur[c][p][0]-arr[c][p][0]-nom
            earlybias[c][p]=cur[c][p][1]-arr[c][p][1]-a.min_ratio*nom
    tb={}
    for t in mesh['taps']:tb.setdefault(t['part'],[]).append(dict(port=t['port'],part=t['part'],xy=t['xy']))
    raw=list(M.DC.seam_pairs(plan,tb))+M.DC.intra_pairs(tb,float(plan.budgets.get('tap_pitch_um',400.)))
    pairs=sorted({tuple(sorted((x[0],x[1]))) for x in raw})
    floor={c:max(((cur[c][u][0]-cur[c][u][1]+cur[c][v][0]-cur[c][v][1])/2-credit[c],u,v) for u,v in pairs) for c in ('TT','FF')}
    rows=[];cols=[];vals=[];rhs=[]
    def add(co,b):
        k=len(rhs)
        for i,v in co.items():rows.append(k);cols.append(i);vals.append(v)
        rhs.append(b)
    gamma=2*N
    for c,shift in [('TT',0),('FF',N)]:
        for u,v in pairs:
            for p,q in ((u,v),(v,u)):
                fixed=arr[c][p][0]+off(p,c)-arr[c][q][1]-off(q,c)+latebias[c][p]-earlybias[c][q]-credit[c]
                add({shift+idx[p]:1.,shift+idx[q]:-a.min_ratio,gamma:-1.},-fixed)
    for p,i in idx.items():
        for x,y,z in hull.equations:add({i:float(x),N+i:float(y)},float(-z))
    A=sp.csr_matrix((vals,(rows,cols)),shape=(len(rhs),gamma+1))
    cost=np.full(gamma+1,1e-6);cost[gamma]=1.
    bounds=[(float(pts[:,0].min()),float(pts[:,0].max()))]*N+[(float(pts[:,1].min()),float(pts[:,1].max()))]*N+[(0.,a.target)]
    r=linprog(cost,A_ub=A,b_ub=np.array(rhs),bounds=bounds,method='highs')
    out={'scope':'PLANNING ONLY: requires nearest physical chain and actual routed TT/FF','success':bool(r.success),'message':r.message,'ports':N,'unique_related_pairs':len(pairs),'constraints':len(rhs),'hull_vertices':len(hull.vertices),'current_uncommon_range_floor_ps':{c:[round(x[0],3),x[1],x[2]] for c,x in floor.items()},'target_limit_ps':a.target,'calibration':str(prev),'baseline':str(base),'min_cells':a.min_cells,'max_cells':a.max_cells,'family':a.family}
    if r.success:
        out['maximum_constraint_residual_ps']=float(np.max(A@r.x-np.array(rhs)))
        if out['maximum_constraint_residual_ps']>.01:raise ValueError('phase LP has infeasible numeric residual')
        out['continuous_related_pair_bound_ps']=float(r.x[gamma]);out['targets']={p:{c:float(arr[c][p][0]+off(p,c)+r.x[shift+i]+latebias[c][p]) for c,shift in [('TT',0),('FF',N)]} for p,i in idx.items()}
        out['added_delay_range_ps']={c:[float(r.x[shift:shift+N].min()),float(r.x[shift:shift+N].max())] for c,shift in [('TT',0),('FF',N)]}
    Path(a.out).write_text(json.dumps(out,indent=1)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='targets'},indent=1))
    return 0 if r.success else 1

if __name__=='__main__':
    p=L.argparse.ArgumentParser(description=__doc__);p.add_argument('dir');p.add_argument('--calibration',required=True);p.add_argument('--plan',required=True);p.add_argument('--libdir',required=True);p.add_argument('--out',required=True);p.add_argument('--target',type=float,default=75.);p.add_argument('--min-ratio',type=float,default=.97);p.add_argument('--family',default='24,12f,4f,2');p.add_argument('--min-cells',type=int,default=2);p.add_argument('--max-cells',type=int,default=14);raise SystemExit(run(p.parse_args()))
