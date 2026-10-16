#!/usr/bin/env python3
"""Independent exact-rectangle audit of actual OpenROAD special-wire readback.
Checks both nets, all via routing enclosures, signal pins, OBS with own PG-pin
subtraction, reserved-column clearance, and no geometry outside macro footprint.
Does not substitute for foundry signoff of a licensed PHY.
"""
import argparse
import bisect
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
        active={};ends=[];buckets=defaultdict(set);span=50000
        for k,(net,r,kind) in enumerate(sorted(shapes,key=lambda s:s[1][1])):
            while ends and ends[0][0]<=r[1]:
                _,j=heapq.heappop(ends)
                if j in active:
                    _,old,_=active.pop(j)
                    for b in range(old[0]//span,(old[2]-1)//span+1):
                        buckets[b].discard(j)
                        if not buckets[b]:del buckets[b]
            possible=set()
            for b in range(r[0]//span,(r[2]-1)//span+1):possible.update(buckets.get(b,()))
            for j in possible:
                other,box,_=active[j]
                if other==net:continue
                comparisons+=1
                if intersect(r,box):shorts.append([layer,net,other,r,box])
            active[k]=(net,r,kind);heapq.heappush(ends,(r[3],k))
            for b in range(r[0]//span,(r[2]-1)//span+1):buckets[b].add(k)
    obs_hits=[];signal_hits=[];signal_spacing=[];checked=0;straps=0
    for i in data['instances']:
        pins=defaultdict(list)
        for n,typ,l,*r in i['pins']:pins[(n,l)].append(transform(r,i))
        signal_bounds={};signal_layer_bounds={}
        for (name,layer),boxes in pins.items():
            if name in ['VDD','VSS']:continue
            b=[min(r[0] for r in boxes),min(r[1] for r in boxes),max(r[2] for r in boxes),max(r[3] for r in boxes)]
            signal_bounds[(name,layer)]=b
            old=signal_layer_bounds.get(layer,b)
            signal_layer_bounds[layer]=[min(old[0],b[0]),min(old[1],b[1]),max(old[2],b[2]),max(old[3],b[3])]
        pin_index={}
        for key,boxes in pins.items():
            boxes=sorted(boxes,key=lambda r:r[1]);pin_index[key]=(boxes,[r[1] for r in boxes],max(r[3]-r[1] for r in boxes))
        obs=defaultdict(list)
        for l,*r in i['obs']:obs[l].append(transform(r,i))
        for l,shapes in layers.items():
            local=[(n,r,k) for n,r,k in shapes if intersect(r,i['bbox'])]
            for net,r,kind in local:
                if l=='M5' and kind=='wire':
                    straps+=1
                    if intersect(r,i['bbox'])!=r:raise ValueError('M5 strap escapes reserved footprint')
                clearance=40 if l=='M8' else 0
                expanded=[r[0]-clearance,r[1]-clearance,r[2]+clearance,r[3]+clearance]
                if l in signal_layer_bounds and intersect(expanded,signal_layer_bounds[l]):
                    for (n,pl),boxes in pins.items():
                        if pl==l and n not in ['VDD','VSS'] and intersect(expanded,signal_bounds[(n,pl)]):
                            for b in boxes:
                                if intersect(r,b):signal_hits.append([i['name'],l,net,n,r,b])
                                elif clearance and intersect(expanded,b):signal_spacing.append([i['name'],l,net,n,r,b])
                for b in obs[l]:
                    hit=intersect(r,b)
                    if hit is None:continue
                    pieces=[hit]
                    if (net,l) in pin_index:
                        boxes,starts,max_height=pin_index[(net,l)]
                        lo=bisect.bisect_left(starts,hit[1]-max_height)
                        hi=bisect.bisect_left(starts,hit[3])
                        for p in boxes[lo:hi]:pieces=[q for part in pieces for q in subtract(part,p)]
                    if pieces:obs_hits.append([i['name'],l,net,r,pieces])
                # M5 wide-wire min spacing in pinned ASAP7 tech is72nm.
                # There are no M5 macro PG pins that could waive this check.
                if l=='M5':
                    expanded=[r[0]-72,r[1]-72,r[2]+72,r[3]+72]
                    for b in obs[l]:
                        if intersect(expanded,b):obs_hits.append([i['name'],'M5_spacing72',net,r,b])
                checked+=1
    result=dict(status='PASS' if not (shorts or obs_hits or signal_hits or signal_spacing) else 'FAIL',shapes=len(data['shapes']),
      orientations=[i['orient'] for i in data['instances']],routing_shapes_inside_macros=checked,m5_straps=straps,
      opposite_net_comparisons=comparisons,shorts=len(shorts),obstruction_violations=len(obs_hits),signal_pin_overlaps=len(signal_hits),m8_signal_spacing40_violations=len(signal_spacing))
    if shorts or obs_hits or signal_hits or signal_spacing:result['examples']=(shorts+obs_hits+signal_hits+signal_spacing)[:8]
    return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('geometry',type=Path);ap.add_argument('--output',type=Path);a=ap.parse_args()
    result=verify(json.loads(a.geometry.read_text()));out=json.dumps(result,indent=2)+'\n';print(out,end='')
    if a.output:a.output.write_text(out)
    if result['status']!='PASS':raise SystemExit(1)
if __name__=='__main__':main()
