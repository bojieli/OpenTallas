#!/usr/bin/env python3
"""Conservative focused pad-chain site model, using pinned prior full-master sizes.

MODEL ONLY: other chains remain unresolved; no phase/native/whole-die claim.
The footprint and every endpoint envelope are checked conservatively, with
fixed pad/stage identities and no extra latency. Run on the fleet.
"""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import re

import numpy as np
from scipy.ndimage import maximum_filter

from row_sites import ROW


def load(p):
    return json.load(gzip.open(p, 'rt') if str(p).endswith('.gz') else open(p))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('sites','layer','manifest','size_manifest','endpoint','stations','out'):
        ap.add_argument('--'+name.replace('_','-'),required=True)
    ap.add_argument('--slot',default='d4f_relay_sink:pgp_NE.command->su_NE1')
    ap.add_argument('--bus', required=True, help='exact relay_splice_v2 bus identity; a slot can contain several chains')
    ap.add_argument('--macro-only', action='store_true', help='diagnostic upper bound: all other relay rows require joint replanning; never a physical pass')
    a=ap.parse_args(); packet,spec,man,sizes,end,stations=(load(getattr(a,n)) for n in
        ('sites','layer','manifest','size_manifest','endpoint','stations'))
    by_inst={i['name']: i for i in spec['instances']}
    splice=next(r for r in spec['relay_splice_v2'] if r['bus']==a.bus)
    sink=a.slot.rsplit('->',1)[1];sinkinfo=splice['sinks'][sink]
    target=[]
    for names in sinkinfo['chain']:
        key=ROW.search(by_inst[names[0]]['note'])[1]
        target.append((key,packet['rows'][key]))
    if any(v['slot']!=a.slot or v['instances']!=names for (_,v),names in zip(target,sinkinfo['chain'])):
        raise ValueError('actual ordered splice stage/slot identity mismatch')
    if not target:raise ValueError('focused slot missing')
    exact={}
    for v in sizes['placement'].values():
        k=v['m'];old=exact.get(k,(0,0));exact[k]=(max(old[0],v['w']),max(old[1],v['h']))
    fallback={}
    def shape(row):
        master=row['master']
        if master in exact:w,h=exact[master]
        else:
            family=re.match(r'(hbfd_(?:land0|land|lh0|lh|rly)_\d+)_',master)
            candidates=[v for k,v in exact.items() if family and k.startswith(family[1]+'_')]
            if not candidates:raise ValueError('no pinned full-master dimensions '+master)
            w,h=max(q[0] for q in candidates),max(q[1] for q in candidates)
            fallback[master]=[w,h]
        return (w*row['tiles'],h) if row['direction'] in ('NS','SN') else (w,h*row['tiles'])
    def paired_bound(x,y,rec,otherxy,other):
        if rec['tiles']!=other['tiles']:raise ValueError('lane count changes across actual ordered stage')
        rw,rh=shape(rec);ow,oh=shape(other);n=rec['tiles']
        rx,ry=(rw/n,rh) if rec['direction'] in ('NS','SN') else (rw,rh/n)
        ox,oy=(ow/n,oh) if other['direction'] in ('NS','SN') else (ow,oh/n)
        result=np.zeros_like(x,dtype=float)
        for t in range(n):
            scale=t-(n-1)/2
            rdx,rdy=(scale*rx,0) if rec['direction'] in ('NS','SN') else (0,scale*ry)
            odx,ody=(scale*ox,0) if other['direction'] in ('NS','SN') else (0,scale*oy)
            bound=np.abs(x+rdx-otherxy[0]-odx)+np.abs(y+rdy-otherxy[1]-ody)+(rx+ry+ox+oy)/2
            result=np.maximum(result,bound)
        return result
    bbox=end['bbox'];goal=np.array([(bbox[0]+bbox[2])/2,(bbox[1]+bbox[3])/2])
    feed=sinkinfo['src'][0]
    parentnode=next(n for n in splice['nodes'] if n['id']==feed)
    pi=by_inst[parentnode['names'][0]];pm=ROW.search(pi['note'])
    parentpt=np.array([float(pm[5]),float(pm[6])])
    parentrec=dict(master=pi['master'],tiles=int(pm[3]),direction=pm[4]);pw,ph=shape(parentrec)
    G=4.32; x0=math.floor((goal[0]-1500)/G)*G;y0=math.floor((goal[1]-1500)/G)*G
    nx=math.ceil(1800/G);ny=math.ceil(3000/G)
    blocked=np.zeros((nx,ny),bool)
    def mark(mask,x,y,w,h):
        lo=max(0,int(math.floor((x-x0)/G)));hi=min(nx,int(math.ceil((x+w-x0)/G)))
        bot=max(0,int(math.floor((y-y0)/G)));top=min(ny,int(math.ceil((y+h-y0)/G)))
        if hi>lo and top>bot:mask[lo:hi,bot:top]=True
    for v in man['placement'].values():
        if not v['m'].startswith(('hbfd_rly','hbfd_lh','hbfd_land')):mark(blocked,v['x'],v['y'],v['w'],v['h'])
    focus={k for k,_ in target}; existing={};missing=set()
    for inst in spec['instances']:
        m=ROW.search(inst.get('note',''))
        if not m or m[1] in focus or m[1] in existing:continue
        rec=dict(master=inst['master'],tiles=int(m[3]),direction=m[4])
        try:w,h=shape(rec)
        except ValueError:missing.add(inst['master']);continue
        existing[m[1]]=(float(m[5]),float(m[6]),w,h)
    if not a.macro_only:
        for x,y,w,h in existing.values():mark(blocked,x-w/2,y-h/2,w,h)
    free0=~blocked;used=np.zeros_like(blocked)
    # Explicit per-window free-cell budget; unlike old consume(), never force
    # demand into an overfull bin or move a stage past reach to find capacity.
    bx=np.floor((x0+(np.arange(nx)+.5)*G)/550).astype(int)
    by=np.floor((y0+(np.arange(ny)+.5)*G)/550).astype(int)
    nby=int(by.max()+1); ids=bx[:,None]*nby+by[None,:]
    capacity=np.bincount(ids.ravel(),weights=free0.ravel()*G*G)*.50
    charged=np.zeros_like(capacity)
    X,Y=np.meshgrid(x0+(np.arange(nx)+.5)*G,y0+(np.arange(ny)+.5)*G,indexing='ij')
    selected={};failure=None;prev=goal;prevhalf=(bbox[2]-bbox[0]+bbox[3]-bbox[1])/2
    # Reserve the wide landing first; greedy padding must not consume its only
    # source-reachable legal footprint. Remaining pads are placed backwards.
    firstkey,firstrec=target[0];fw,fh=shape(firstrec);firsthalf=(fw+fh)/2
    fwx=2*math.ceil((fw/2+G)/G)+1;fwy=2*math.ceil((fh/2+G)/G)+1
    fc=maximum_filter(blocked.astype(np.uint8),size=(fwx,fwy),mode='constant',cval=1)
    fd=np.abs(X-parentpt[0])+np.abs(Y-parentpt[1])
    first_ok=(fc==0)&(paired_bound(X,Y,firstrec,parentpt,parentrec)<=395)
    choices=np.argwhere(first_ok)
    firstpt=None
    for j in np.argsort(fd[first_ok],kind='stable'):
        ix,iy=choices[j];lo,hi=ix-fwx//2,ix+fwx//2+1;bot,top=iy-fwy//2,iy+fwy//2+1
        charge=np.bincount(ids[lo:hi,bot:top].ravel(),minlength=len(capacity))*G*G
        if np.any(charged+charge>capacity+1e-6):continue
        charged+=charge;used[lo:hi,bot:top]=True
        firstpt=np.array([round(float(X[ix,iy]),1),round(float(Y[ix,iy]),1)])
        selected[firstkey]=dict(xy=firstpt.tolist(),footprint=[fw,fh]);break
    if firstpt is None:raise ValueError('no source-reachable footprint/capacity-legal reserved landing')
    prevrec=None
    for reverse,(key,rec) in enumerate(reversed(target[1:])):
        w,h=shape(rec);wx=2*math.ceil((w/2+G)/G)+1;wy=2*math.ceil((h/2+G)/G)+1
        collision=maximum_filter((blocked|used).astype(np.uint8),size=(wx,wy),mode='constant',cval=1)
        half=(w+h)/2
        distance=np.abs(X-prev[0])+np.abs(Y-prev[1])
        hop_bound=(distance+half+prevhalf) if prevrec is None else paired_bound(X,Y,rec,prev,prevrec)
        ok=(collision==0)&(hop_bound<=395)
        remaining=len(target)-reverse-2
        if remaining==0:
            ok &= paired_bound(X,Y,rec,firstpt,firstrec)<=395
        else:
            ok &= np.abs(X-firstpt[0])+np.abs(Y-firstpt[1])<remaining*230+200
        indices=np.argwhere(ok)
        if not len(indices):
            legal=collision==0
            failure=dict(row=key,reason='no footprint-legal <=395um all-pin-envelope site',placed=len(selected),
                         free_footprint_centres=int(legal.sum()),
                         nearest_all_pin_bound_um=float(np.min(distance[legal])+half+prevhalf) if legal.any() else None)
            break
        local_use=np.divide(charged[ids],capacity[ids],out=np.ones_like(X),where=capacity[ids]>0)
        scores=.10*distance[ok]+300*local_use[ok]+.005*(np.abs(X[ok]-firstpt[0])+np.abs(Y[ok]-firstpt[1]))
        found=False
        for j in np.argsort(scores,kind='stable'):
            ix,iy=indices[j];lo,hi=ix-wx//2,ix+wx//2+1;bot,top=iy-wy//2,iy+wy//2+1
            charge=np.bincount(ids[lo:hi,bot:top].ravel(),minlength=len(capacity))*G*G
            if np.any(charged+charge>capacity+1e-6):continue
            charged+=charge;used[lo:hi,bot:top]=True
            xy=[round(float(X[ix,iy]),1),round(float(Y[ix,iy]),1)]
            selected[key]=dict(xy=xy,footprint=[w,h]);prev=np.array(xy);prevhalf=half;prevrec=rec;found=True;break
        if not found:failure=dict(row=key,reason='all reachable legal footprints exceed50pct actualfree-cell window budget',placed=len(selected));break
    ratio=float(np.max(np.divide(charged,capacity,out=np.zeros_like(charged),where=capacity>0)))
    envelope=[]
    if failure is None:
        previous=parentpt;previousrec=parentrec;phalf=(pw+ph)/2
        for key,rec in target:
            v=selected[key];xy=np.array(v['xy']);half=sum(v['footprint'])/2
            envelope.append(float(paired_bound(xy[0],xy[1],rec,previous,previousrec)))
            previous=xy;previousrec=rec;phalf=half
        envelope.append(float(np.abs(previous-goal).sum()+phalf+(bbox[2]-bbox[0]+bbox[3]-bbox[1])/2))
        if max(envelope)>395.2:failure=dict(reason='independent post-allocation endpoint bound failed',maximum=max(envelope))
    verdict='FOCUSED_MODEL_PASS' if failure is None and not missing else 'FOCUSED_MODEL_FAIL'
    if a.macro_only: verdict='JOINT_REPLAN_UPPER_BOUND_'+('FEASIBLE' if failure is None and not missing else 'FAIL')
    result=dict(verdict=verdict,slot=a.slot,bus=a.bus,stages=len(target),placed=len(selected),failure=failure,
                selected=selected,missing_master_dimensions=sorted(missing),max_window_ratio=ratio,
                conservative_family_dimension_fallbacks=fallback,
                other_relay_rows_held_fixed=not a.macro_only,
                all_pin_envelope_hops_um=envelope,
                input_sha256={n:hashlib.sha256(Path(getattr(a,n)).read_bytes()).hexdigest() for n in
                              ('sites','layer','manifest','size_manifest','endpoint','stations')},
                geometry_qualified=False,clock_phase_qualified=False,
                scope='focused source-ordered chain only; prior full-master dimensions conservative; same stagecount; all-pin bounding envelopes; no whole-die/phase/native claim')
    Path(a.out).write_text(json.dumps(result,indent=1)+'\n')
    print('FOCUSED_PAD_MODEL',verdict,'placed',len(selected),'/',len(target),'failure',failure,'missing_dims',len(missing),'maxwindow',ratio)
    return 0 if verdict.endswith('PASS') else 1


if __name__=='__main__':raise SystemExit(main())
