#!/usr/bin/env python3
"""Allocate actual per-bit cells along declared channel paths, preserving macro-free wires.

This refines channel_paths.py's centroids into the kit's explicit cell-site
contract. It reserves 40um per endpoint cohort in each reach-bounded hop, and
keeps every candidate target on the existing channel polylines.
"""
import argparse
import json
import math
import sys
from collections import deque
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'tools/die_plan'))
sys.path.insert(0,str(ROOT))
import check as C
import schema as S
from gen_phys import type_pins
from ft_sites import _extent
from tools.die_trial.legal_sites import RowAllocator
from channel_paths import blocked,boxes


def legal(a,b,obs):
    return any(not blocked(a,c,obs) and not blocked(c,b,obs)
               for c in ((a[0],b[1]),(b[0],a[1])))


def chain(targets,a,b,budget,radius,minimum,obs):
    first,last=_extent(a,targets),_extent(b,targets)
    parents=np.full(len(targets),-2,dtype=int)
    starts=np.flatnonzero(first+radius<=budget)
    queue=deque(map(int,starts));parents[starts]=-1;end=None
    while queue:
        v=queue.popleft()
        if last[v]+radius<=budget:end=v;break
        dist=np.abs(targets-targets[v]).sum(axis=1)
        near=np.flatnonzero((dist<=budget-2*radius)&(parents==-2))
        for n in near[np.argsort(last[near])]:
            if legal(targets[v],targets[n],obs):parents[n]=v;queue.append(int(n))
    if end is None:raise ValueError('no reach-bounded chain along declared channels')
    ids=[]
    while end>=0:ids.append(end);end=parents[end]
    ids.reverse()
    while len(ids)+1<minimum:
        if len(ids)==1:ids.append(ids[0]);continue
        j=max(range(len(ids)-1),key=lambda j:float(np.abs(targets[ids[j]]-targets[ids[j+1]]).sum()))
        u,v=ids[j:j+2];mid=(targets[u]+targets[v])/2
        near=np.flatnonzero((np.abs(targets-targets[u]).sum(axis=1)<=budget-2*radius)&
                            (np.abs(targets-targets[v]).sum(axis=1)<=budget-2*radius))
        choices=[int(n) for n in near if legal(targets[u],targets[n],obs) and legal(targets[n],targets[v],obs)]
        if not choices:raise ValueError('cannot preserve existing cycle count in channel')
        best=min(choices,key=lambda n:float(np.abs(targets[n]-mid).sum()))
        ids.insert(j+1,best)
    return ids


def targets_on_path(points,obs):
    out=[]
    for a,b in zip(points,points[1:]):
        corners=[c for c in ((a[0],b[1]),(b[0],a[1])) if not blocked(a,c,obs) and not blocked(c,b,obs)]
        if not corners:raise ValueError('centroid path itself crosses a core')
        path=[a,corners[0],b]
        for u,v in zip(path,path[1:]):
            n=max(1,math.ceil(C.plen([u,v])/8.64))
            out.extend((u[0]+(v[0]-u[0])*i/n,u[1]+(v[1]-u[1])*i/n) for i in range(n+1))
    return np.unique(np.round(np.array(out),6),axis=0)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('plan');ap.add_argument('out');ap.add_argument('--types',nargs='+',required=True)
    args=ap.parse_args();raw=json.load(open(args.plan));P=S.Plan(raw);ledger=[]
    for tn in args.types:
        t=raw['partition_types'][tn];W,H=t['outline_um'];obs=boxes(t)
        pins={}
        for bus,bit,layer,x,y,face in type_pins(P,tn):pins[(bus,bit)]=(x,y)
        allocator=RowAllocator((4.32,4.32,W-4.32,H-4.32),blocked=obs,cell_size=(1.404,.27),column_pitch=2.16,row_pitch=.27,origin=(4.32,4.32))
        for slot in sorted(t['ft_slots'],key=lambda s:-s['width']):
            name=slot['name'];n=slot['width']+1;k=slot['stations']
            a=np.array([pins[(name+'_i',i)] for i in range(n)]);b=np.array([pins[(name+'_o',i)] for i in range(n)])
            centre=[tuple(v) for v in slot.get('regs_um',[])]+[tuple(b.mean(axis=0))]
            if len(centre)<2:raise ValueError(f'{tn}/{name}: channel centroids required')
            targets=targets_on_path(centre,obs);radius=40.;budget=403.;used=set(allocator.used);denied=set()
            while True:
                allocator.used=set(used);free=targets[[i not in denied for i in range(len(targets))]]
                original=[i for i in range(len(targets)) if i not in denied]
                ids=chain(free,a,b,budget,radius,k,obs);points=[];stats=[]
                for i in ids:
                    try:p,st=allocator.allocate(free[i],n,max_radius_um=radius)
                    except ValueError:denied.add(original[i]);break
                    points.append(p);stats.append(st)
                else:break
            seq=[a,*points,b];worst=max(float(np.abs(v-u).sum(axis=1).max()) for u,v in zip(seq,seq[1:]))
            crossed=sum(not legal(u,v,obs) for aa,bb in zip(seq,seq[1:]) for u,v in zip(aa,bb))
            if worst>budget+1e-6 or crossed:raise ValueError(f'{tn}/{name}: actual hop{worst:g},core-crossing bits{crossed}')
            slot['stations']=len(points)+1;slot['regs_um']=[a.mean(axis=0).round(6).tolist()]+[free[i].round(6).tolist() for i in ids]
            slot['bit_site_cell_um']=[1.404,.27];slot['bit_sites_um']=[(p-np.array([.702,.135])).round(6).tolist() for p in points]
            row=dict(type=tn,slot=name,stations=[k,slot['stations']],actual_max_hop_um=round(worst,6),core_crossing_bits=crossed)
            ledger.append(row);print(json.dumps(row),flush=True)
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    (out/'die_plan.json').write_text(json.dumps(raw,indent=1)+'\n');(out/'sites_ledger.json').write_text(json.dumps(ledger,indent=1)+'\n')

if __name__=='__main__':main()
