#!/usr/bin/env python3
"""Independent exact-rectangle audit of actual OpenROAD special-wire readback.
Checks both nets, all via routing enclosures, signal pins, OBS with own PG-pin
subtraction, reserved-column clearance, and no geometry outside macro footprint.
Does not substitute for foundry signoff of a licensed PHY.
"""
import argparse
from collections import defaultdict
import heapq
import json
from pathlib import Path

def intersect(a,b):
    r=[max(a[0],b[0]),max(a[1],b[1]),min(a[2],b[2]),min(a[3],b[3])]
    return r if r[0]<r[2] and r[1]<r[3] else None

def subtract(a,b):
    c=intersect(a,b)
    if c is None: return [a]
    x,y,z,t=c;u,v,w,h=a
    return [r for r in [[u,v,x,h],[z,v,w,h],[x,v,z,y],[x,t,z,h]] if r[0]<r[2] and r[1]<r[3]]

def transform(r,i):
    a,b,c,d=r;w=i['width'];h=i['height'];o=i['orient'];x,y=i['bbox'][:2]
    if o in ['MY','R180']:a,c=w-c,w-a
    if o in ['MX','R180']:b,d=h-d,h-b
    if o not in ['R0','MX','MY','R180']:raise ValueError(o)
    return [a+x,b+y,c+x,d+y]

def verify(data):
    layers=defaultdict(list)
    for n,l,*rest in data['shapes']:layers[l].append((n,rest[:4],rest[4]))
    # Sweep in Y: include every SWire routing shape and via enclosure.
    shorts=[];comparisons=0
    for layer, shapes in layers.items():
        active={};ends=[]
        for k,(net,r,kind) in enumerate(sorted(shapes,key=lambda s:s[1][1])):
            while ends and ends[0][0]<=r[1]:
                _,j=heapq.heappop(ends);active.pop(j,None)
            for other,box,_ in active.values():
                if other==net:continue
                comparisons+=1
                if intersect(r,box):shorts.append([layer,net,other,r,box])
            active[k]=(net,r,kind);heapq.heappush(ends,(r[3],k))
    obs_hits=[];signal_hits=[];checked=0;straps=0
    for i in data['instances']:
        pins=defaultdict(list)
        for n,typ,l,*r in i['pins']:pins[(n,l)].append(transform(r,i))
        obs=defaultdict(list)
        for l,*r in i['obs']:obs[l].append(transform(r,i))
        for l,shapes in layers.items():
            local=[(n,r,k) for n,r,k in shapes if intersect(r,i['bbox'])]
            for net,r,kind in local:
                if l=='M5' and kind=='wire':
                    straps+=1
                    if intersect(r,i['bbox'])!=r:raise ValueError('M5 strap escapes reserved footprint')
                for (n,pl),boxes in pins.items():
                    if pl==l and n not in ['VDD','VSS']:
                        for b in boxes:
                            if intersect(r,b):signal_hits.append([i['name'],l,net,n,r,b])
                for b in obs[l]:
                    hit=intersect(r,b)
                    if hit is None:continue
                    pieces=[hit]
                    for p in pins[(net,l)]:pieces=[q for part in pieces for q in subtract(part,p)]
                    if pieces:obs_hits.append([i['name'],l,net,r,pieces])
                # M5 wide-wire min spacing in pinned ASAP7 tech is72nm.
                # There are no M5 macro PG pins that could waive this check.
                if l=='M5':
                    expanded=[r[0]-72,r[1]-72,r[2]+72,r[3]+72]
                    for b in obs[l]:
                        if intersect(expanded,b):obs_hits.append([i['name'],'M5_spacing72',net,r,b])
                checked+=1
    result=dict(status='PASS' if not (shorts or obs_hits or signal_hits) else 'FAIL',shapes=len(data['shapes']),
      orientations=[i['orient'] for i in data['instances']],routing_shapes_inside_macros=checked,m5_straps=straps,
      opposite_net_comparisons=comparisons,shorts=len(shorts),obstruction_violations=len(obs_hits),signal_pin_overlaps=len(signal_hits))
    if shorts or obs_hits or signal_hits:result['examples']=(shorts+obs_hits+signal_hits)[:8]
    return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('geometry',type=Path);ap.add_argument('--output',type=Path);a=ap.parse_args()
    result=verify(json.loads(a.geometry.read_text()));out=json.dumps(result,indent=2)+'\n';print(out,end='')
    if a.output:a.output.write_text(out)
    if result['status']!='PASS':raise SystemExit(1)
if __name__=='__main__':main()
