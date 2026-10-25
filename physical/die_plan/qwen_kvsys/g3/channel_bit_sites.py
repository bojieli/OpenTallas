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
    am,bm=a.mean(axis=0),b.mean(axis=0)
    axis_start=(np.abs(targets-am).min(axis=1)<1e-4)
    axis_end=(np.abs(targets-bm).min(axis=1)<1e-4)
    starts=np.flatnonzero((first+radius<=budget)&axis_start)
    queue=deque(map(int,starts));parents[starts]=-1;end=None
    while queue:
        v=queue.popleft()
        if last[v]+radius<=budget and axis_end[v]:end=v;break
        dist=np.abs(targets-targets[v]).sum(axis=1)
        near=np.flatnonzero((dist<=budget-2*radius)&(parents==-2))
        for n in near[np.argsort(last[near])]:
            if np.abs(targets[v]-targets[n]).min()<1e-4 and legal(targets[v],targets[n],obs):parents[n]=v;queue.append(int(n))
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
        choices=[int(n) for n in near if np.abs(targets[u]-targets[n]).min()<1e-4 and np.abs(targets[n]-targets[v]).min()<1e-4 and legal(targets[u],targets[n],obs) and legal(targets[n],targets[v],obs)]
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


def corridor(a,b,obs,W,H):
    lo,hi=0.,W
    bottom,top=0.,H
    if C.plen([a,b])<1e-4:return lo,bottom,hi,top
    if abs(a[0]-b[0])<1e-4:
        x=(a[0]+b[0])/2
        for x0,y0,x1,y1 in obs:
            if max(min(a[1],b[1]),y0)<min(max(a[1],b[1]),y1):
                if x1<=x+1e-4:lo=max(lo,x1)
                elif x0>=x-1e-4:hi=min(hi,x0)
    elif abs(a[1]-b[1])<1e-4:
        y=(a[1]+b[1])/2
        for x0,y0,x1,y1 in obs:
            if max(min(a[0],b[0]),x0)<min(max(a[0],b[0]),x1):
                if y1<=y+1e-4:bottom=max(bottom,y1)
                elif y0>=y-1e-4:top=min(top,y0)
    else:raise ValueError('unregistered channel bend')
    return lo,bottom,hi,top

def allocate_cohort(allocator,target,previous,following,n,radius,obs,W,H):
    a=corridor(previous,target,obs,W,H);b=corridor(target,following,obs,W,H)
    x0,y0,x1,y1=max(a[0],b[0]),max(a[1],b[1]),min(a[2],b[2]),min(a[3],b[3])
    walls=[(0.,0.,x0,H),(x1,0.,W,H),(0.,0.,W,y0),(0.,y1,W,H)]
    local=RowAllocator(allocator.bounds,blocked=obs+walls,cell_size=(1.404,.27),column_pitch=2.16,row_pitch=.27,origin=(4.32,4.32))
    local.used=set(allocator.used)
    p,stats=local.allocate(target,n,max_radius_um=radius)
    allocator.used=set(local.used)
    return p,stats


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
                for j,i in enumerate(ids):
                    previous=free[ids[j-1]] if j else a.mean(axis=0)
                    following=free[ids[j+1]] if j+1<len(ids) else b.mean(axis=0)
                    try:p,st=allocate_cohort(allocator,free[i],previous,following,n,radius,obs,W,H)
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
