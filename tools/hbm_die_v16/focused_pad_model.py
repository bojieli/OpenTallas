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
    a=ap.parse_args(); packet,spec,man,sizes,end,stations=(load(getattr(a,n)) for n in
        ('sites','layer','manifest','size_manifest','endpoint','stations'))
    target=[(k,v) for k,v in packet['rows'].items() if v['slot']==a.slot]
    target.sort(key=lambda p:(int('_pa' in p[0]),int(p[0].rsplit('_',1)[1])))
    if not target:raise ValueError('focused slot missing')
    exact={}
    for v in sizes['placement'].values():
        k=v['m'];old=exact.get(k,(0,0));exact[k]=(max(old[0],v['w']),max(old[1],v['h']))
    def shape(row):
        if row['master'] not in exact:raise ValueError('no pinned full-master dimensions '+row['master'])
        w,h=exact[row['master']]
        return (w*row['tiles'],h) if row['direction'] in ('NS','SN') else (w,h*row['tiles'])
    bbox=end['bbox'];goal=np.array([(bbox[0]+bbox[2])/2,(bbox[1]+bbox[3])/2])
    row=next(r for r in stations['rows'] if r['driver']==a.slot.split(':',1)[1].split('->')[0])
    towards=[t for t in row['stations'] if t['toward']=='su_NE1']
    parent=max(towards,key=lambda p:p['depth']);parentpt=np.array([parent['x'],parent['y']])
    # The actual forwarded row has the same lane count as its sink landing.
    parentmaster='hbfd_lh_136_'+parent['master'].rsplit('_',1)[1]
    pw,ph=shape(dict(master=parentmaster,tiles=target[0][1]['tiles'],direction=parent['master'].rsplit('_',1)[1]))
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
    for reverse,(key,rec) in enumerate(reversed(target)):
        w,h=shape(rec);wx=2*math.ceil((w/2+G)/G)+1;wy=2*math.ceil((h/2+G)/G)+1
        collision=maximum_filter((blocked|used).astype(np.uint8),size=(wx,wy),mode='constant',cval=1)
        half=(w+h)/2
        distance=np.abs(X-prev[0])+np.abs(Y-prev[1])
        ok=(collision==0)&(distance+half+prevhalf<=395)
        remaining=len(target)-reverse-1
        if remaining==0:
            ok &= np.abs(X-parentpt[0])+np.abs(Y-parentpt[1])+half+(pw+ph)/2<=395
        else:
            ok &= np.abs(X-parentpt[0])+np.abs(Y-parentpt[1])<remaining*230+200
        indices=np.argwhere(ok)
        if not len(indices):failure=dict(row=key,reason='no footprint-legal <=395um all-pin-envelope site',placed=len(selected));break
        scores=distance[ok]+.015*(np.abs(X[ok]-goal[0])+np.abs(Y[ok]-goal[1]))
        found=False
        for j in np.argsort(scores,kind='stable'):
            ix,iy=indices[j];lo,hi=ix-wx//2,ix+wx//2+1;bot,top=iy-wy//2,iy+wy//2+1
            charge=np.bincount(ids[lo:hi,bot:top].ravel(),minlength=len(capacity))*G*G
            if np.any(charged+charge>capacity+1e-6):continue
            charged+=charge;used[lo:hi,bot:top]=True
            xy=[round(float(X[ix,iy]),1),round(float(Y[ix,iy]),1)]
            selected[key]=dict(xy=xy,footprint=[w,h]);prev=np.array(xy);prevhalf=half;found=True;break
        if not found:failure=dict(row=key,reason='all reachable legal footprints exceed50pct actualfree-cell window budget',placed=len(selected));break
    ratio=float(np.max(np.divide(charged,capacity,out=np.zeros_like(charged),where=capacity>0)))
    verdict='FOCUSED_MODEL_PASS' if failure is None and not missing else 'FOCUSED_MODEL_FAIL'
    result=dict(verdict=verdict,slot=a.slot,stages=len(target),placed=len(selected),failure=failure,
                selected=selected,missing_master_dimensions=sorted(missing),max_window_ratio=ratio,
                input_sha256={n:hashlib.sha256(Path(getattr(a,n)).read_bytes()).hexdigest() for n in
                              ('sites','layer','manifest','size_manifest','endpoint','stations')},
                geometry_qualified=False,clock_phase_qualified=False,
                scope='focused source-ordered chain only; prior full-master dimensions conservative; same stagecount; all-pin bounding envelopes; no whole-die/phase/native claim')
    Path(a.out).write_text(json.dumps(result,indent=1)+'\n')
    print('FOCUSED_PAD_MODEL',verdict,'placed',len(selected),'/',len(target),'failure',failure,'missing_dims',len(missing),'maxwindow',ratio)
    return 0 if verdict.endswith('PASS') else 1


if __name__=='__main__':raise SystemExit(main())
