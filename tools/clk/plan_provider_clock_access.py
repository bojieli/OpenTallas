#!/usr/bin/env python3
"""Select real M1 clock-pin access points (register CLK, or leaf-driver trunk-side inverter A) with legal complete M1..M7 lower stacks.

All master obstructions, actual signal pins, PG, and retained clock escapes are
blocking. A same-net clock conductor alone may overlap. This is lower access
planning, never route/IR/timing qualification; M7 risers/M8 landings stay open.
"""
from __future__ import annotations
import argparse
from collections import defaultdict, Counter
import copy
import hashlib
import json
import math
from pathlib import Path
import time
import provider_clock_loads as P

SPACING={'M1':18,'M2':18,'M3':18,'M4':24,'M5':24,'M6':32,'M7':32}


def candidate_points(load, via12):
    hx,hy=via12;seen=set()
    for ly,x0,y0,x1,y1 in load['shapes_dbu']:
        if ly!='M1' or x1-x0<2*hx or y1-y0<2*hy:continue
        xs=[round((x0+x1)/2),x0+hx,x1-hx]
        ys=[round((y0+y1)/2),y0+hy,y1-hy]+list(range(y0+hy,y1-hy+1,4))
        for y in ys:
            for x in xs:
                if (x,y) not in seen and x0+hx<=x<=x1-hx and y0+hy<=y<=y1-hy:
                    seen.add((x,y));yield x,y


def stack_bounds(tech,dbu):
    row=dict(net='clock',xy=[0,0])
    grouped=defaultdict(list)
    for _,ly,*r in P.lower_escape_shapes(dict(rows=[row]),tech,dbu):
        grouped[ly].append([round(v*dbu) for v in r])
    return {ly:(min(r[0] for r in rr),min(r[1] for r in rr),max(r[2] for r in rr),max(r[3] for r in rr)) for ly,rr in grouped.items()}


def overlap(a,b):return a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    for key in ('geometry','loads','graph','via-facts','out'):ap.add_argument('--'+key,type=Path,required=True)
    ap.add_argument('--retained-clock',type=Path,action='append',default=[])
    ap.add_argument('--reserved-power',type=Path,action='append',default=[])
    a=ap.parse_args(argv);a.out.mkdir(parents=True,exist_ok=True);t=time.time()
    import numpy as np
    from shapely import box
    from shapely.strtree import STRtree
    g=json.loads(a.geometry.read_text());inv=json.loads(a.loads.read_text());graph=json.loads(a.graph.read_text());vf=json.loads(a.via_facts.read_text());D=g['dbu']
    if D!=inv['dbu'] or D!=vf['dbu']:raise ValueError('geometry/CLK/tech database units differ')
    pin_net={};actual_clk=defaultdict(list)
    for n in graph['nets']:
        if not n['drv'].startswith('port:'):pin_net[n['drv'],'Y']=n['name']
        for ld in n['loads']:
            if not ld.startswith('port:'):pin_net[ld,'A']=n['name']
    for row in inv['loads']:pin_net[row['inst'],P.load_pin(row)]=row['net']
    b=defaultdict(list);meta=defaultdict(list)
    for owner,pin,ly,*r in g['signal_shapes']:
        if ly not in SPACING:continue
        b[ly].append(r);meta[ly].append((pin_net.get((owner,pin)),owner+'/'+pin,'signal'))
        if pin in ('CLK','A'):actual_clk[owner,pin].append([ly,*r])
    for row in inv['loads']:
        if sorted(map(tuple,row['shapes_dbu']))!=sorted(map(tuple,actual_clk[row['inst'],P.load_pin(row)])):
            raise ValueError('CLK pin inventory differs from actual source: '+row['inst'])
    for owner,ly,*r in g['obstructions']:
        if ly in SPACING:b[ly].append(r);meta[ly].append((None,owner,'OBS'))
    for net,ly,*r in g['existing_supplies']:
        if ly in SPACING:b[ly].append(r);meta[ly].append((net,net,'PG'))
    for file in a.retained_clock:
        for net,ly,*r in json.loads(file.read_text()):
            if ly in SPACING:b[ly].append([round(v*D) for v in r]);meta[ly].append((net,net,'retained_clock'))
    for file in a.reserved_power:
        for net,ly,*r in json.loads(file.read_text()):
            if net not in ('VDD','VSS'):raise ValueError('reserved power is not VDD/VSS')
            if ly in SPACING:b[ly].append([round(v*D) for v in r]);meta[ly].append((net,net,'planned_PG'))
    trees={};arrays={}
    for ly,rr in b.items():
        ar=np.asarray(rr,dtype=float);arrays[ly]=ar;trees[ly]=STRtree(box(ar[:,0],ar[:,1],ar[:,2],ar[:,3]))
    del b
    print('ACTUAL_INDEX_READY',round(time.time()-t,2),flush=True)
    tech=vf['tech_vias_dbu'];bounds=stack_bounds(tech,D);v12=next(r[1:] for r in tech['VIA12'] if r[0]=='M1');via12=(max(abs(v12[0]),abs(v12[2])),max(abs(v12[1]),abs(v12[3])))
    placed=defaultdict(lambda:defaultdict(list));BIN=2160;reasons=Counter();failed=[];changes=0;shapes=[];rows=[]
    def bins(r):
        for x in range(math.floor(r[0]/BIN),math.floor(r[2]/BIN)+1):
            for y in range(math.floor(r[1]/BIN),math.floor(r[3]/BIN)+1):yield x,y
    def clear(net,ly,r):
        sp=SPACING[ly];q=(r[0]-sp,r[1]-sp,r[2]+sp,r[3]+sp)
        if q[0]<0 or q[1]<0 or q[2]>g['die_dbu'][2] or q[3]>g['die_dbu'][3]:return False
        for ix in trees[ly].query(box(*q)):
            bn,owner,kind=meta[ly][ix]
            if bn==net:continue
            if overlap(q,arrays[ly][ix]):reasons[ly+':'+kind]+=1;return False
        for key in bins(q):
            for bn,other in placed[ly][key]:
                if bn!=net and overlap(q,other):reasons[ly+':new_clock']+=1;return False
        return True
    # Keep input order deterministic. A later pin cannot steal an earlier
    # allocated unlike-net stack. Every accepted choice is fully reserved.
    for index,load in enumerate(inv['loads']):
        selected=None
        for x,y in candidate_points(load,via12):
            ss=[(ly,(x+q[0],y+q[1],x+q[2],y+q[3])) for ly,q in bounds.items()]
            if all(clear(load['net'],ly,r) for ly,r in ss):selected=(x,y,ss);break
        if selected is None:
            # A native partition pin fence may obstruct the upper column even
            # though the real M1 CLK access itself is clear. Escape at M3,
            # before any M4/M5/M7 fence, using one bounded physical jog.
            for x,y in candidate_points(load,via12):
                for distance in (32,64,96,128,192,256):
                    for dx,dy in ((0,-distance),(0,distance),(-distance,0),(distance,0)):
                        trial=dict(net=load['net'],xy=[x/D,y/D],upper_xy=[(x+dx)/D,(y+dy)/D])
                        ss=[(ly,tuple(round(v*D) for v in r)) for _,ly,*r in P.lower_escape_shapes(dict(rows=[trial]),tech,D)]
                        if all(clear(load['net'],ly,r) for ly,r in ss):selected=(x,y,ss,dx,dy);break
                    if selected:break
                if selected:break
        if selected is None:failed.append(dict(inst=load['inst'],stage=load['stage'],net=load['net'],pin=P.load_pin(load),cause='no all-layer-clear stack or bounded M3 jog on actual M1 pin'));continue
        x,y,ss=selected[:3]
        original=P.pin_entry(load,D,via12)['xy'];changes+=int(original!=[x/D,y/D]);load['entry_xy_dbu']=[x,y]
        if len(selected)>3:load['upper_xy_dbu']=[x+selected[3],y+selected[4]]
        load['entry_xy_dbu']=[x,y];load['access_basis']='actual M1 pin + full lower-stack signal/OBS/PG clearance'
        ep=P.pin_entry(load,D,via12);rows.append(dict(port=f'provider_clk_{index:05d}',stage=load['stage'],**ep))
        for ly,r in ss:
            for key in bins(r):placed[ly][key].append((load['net'],r))
        if index%1000==0:print('PIN',index,'selected',len(rows),'failed',len(failed),'sec',round(time.time()-t,2),flush=True)
    report=dict(status='LOWER_ACCESS_GEOMETRY_PASS' if not failed else 'INCOMPLETE_NO_ROUTE',physical_route=False,timing_qualified=False,loads=len(inv['loads']),selected=len(rows),failed=len(failed),changed_access_points=changes,rows=rows,failures=failed,rejections=dict(reasons),elapsed_s=time.time()-t,scope='Actual M1..M7 lower escape only; no M7 riser/M8 landing/IR/timing qualification.')
    (a.out/'access_report.json').write_text(json.dumps(report)+'\n')
    (a.out/'clock_loads_access.json').write_text(json.dumps(inv)+'\n')
    shapes=P.lower_escape_shapes(report,tech,D)
    (a.out/'lower_escape_reserved.json').write_text(json.dumps(shapes)+'\n')
    print('SUMMARY',report['status'],'selected',len(rows),'failed',len(failed),'changed',changes,'sec',round(time.time()-t,2),flush=True)
    return 0 if not failed else 1

if __name__=='__main__':raise SystemExit(main())
