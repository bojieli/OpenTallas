#!/usr/bin/env python3
"""Attribute current station demand and source-pin flow cuts before floorplan edits.

All-die flow cuts are payload-only lower bounds, using endpoint separation
(independent of unknown detailed routing). Local cell demands are the present
station sites, not a proof that no different placement can work. Macro M1-M5
obstruction and M6+ open assumptions match the r12 SYNTH abstracts; this model
cannot qualify a routed die or substitute for actual GRT/STA.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path


def md(a,b):
    return abs(a[0]-b[0])+abs(a[1]-b[1])


def union_length(intervals):
    end=-math.inf; total=0
    for a,b in sorted(intervals):
        total += max(0,b-max(a,end));end=max(end,b)
    return total


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('stations');ap.add_argument('manifest');ap.add_argument('report');ap.add_argument('--out',required=True)
    a=ap.parse_args()
    s,m,r=(json.load(open(p)) for p in (a.stations,a.manifest,a.report))
    W,H=m['die_um']; width=r['capacity']['windows']['window_um']
    windows=r['capacity']['windows']['worst'][:8]
    segments=[]; sites=[]; badpins=[]
    for row in s['rows']:
        bits=row['bits']; tilewidth=48 if bits<=48 else624
        side=min(max(10.8,(2*tilewidth+8)/24),max(21.6,(2*tilewidth+8)*.048*1.5/.9/4))
        area=math.ceil(bits/tilewidth)*side**2*1.2
        pins=row.get('pins') or {};root=pins.get('driver');stations=row['stations']
        for i,t in enumerate(stations):
            pt=[t['x'],t['y']];par=t.get('parent')
            src=root if par is None else [stations[par]['x'],stations[par]['y']]
            if src is not None:segments.append((src,pt,bits,row['driver']))
            sites.append((pt,area,row['driver'],'station'))
        for sink in row['sinks']:
            dst=(pins.get('sinks') or {}).get(sink)
            towards=[t for t in stations if t.get('toward')==sink]
            if dst is not None and towards:
                t=max(towards,key=lambda x:x['depth']);segments.append(([t['x'],t['y']],dst,bits,row['driver']))
        for p in row.get('pads') or []:
            sites.append(([p['x'],p['y']],area*p['stages'],row['driver'],'equal_age_pad'))
        if root is not None:
            owner=row['driver'].split('.',1)[0];box=m['placement'].get(owner)
            if box and box['x']<root[0]<box['x']+box['w'] and box['y']<root[1]<box['y']+box['h']:
                badpins.append(dict(driver=row['driver'],root=root,bits=bits))
    result=[]
    for ratio,(x,y),demand,capacity in windows:
        near=[q for q in sites if x<=q[0][0]<x+width and y<=q[0][1]<y+width]
        attrib=Counter()
        for _,area,driver,kind in near:attrib[(driver,kind)]+=area
        cut=[]
        for axis,p,span in [(0,x+width/2,H),(1,y+width/2,W)]:
            crossings=[q for q in segments if min(q[0][axis],q[1][axis])<p<max(q[0][axis],q[1][axis])]
            intervals=[]
            for box in m['placement'].values():
                start=box['x'] if axis==0 else box['y'];size=box['w'] if axis==0 else box['h']
                if start<=p<=start+size:
                    st=box['y'] if axis==0 else box['x'];sz=box['h'] if axis==0 else box['w']
                    intervals.append((max(0,st),min(span,st+sz)))
            lower_open=max(0,span-union_length(intervals))
            # Preferred directions: M4/M6/M8 H, M5/M7 V. GRT adjustments
            # M4/5=.30, M6/7=.146, M8=.346 (including .20 PG reserve).
            layers={'M4' if axis==0 else 'M5':lower_open/.048*.70,
                    'M6' if axis==0 else 'M7':span/.064*.854}
            if axis==0:layers['M8']=span/.080*.654
            bits=sum(q[2] for q in crossings)
            cut.append(dict(axis='x' if axis==0 else 'y',coordinate_um=p,payload_lower_bound=bits,
                            payload_segments=len(crossings),routing_tracks_model=layers,
                            ratio=bits/sum(layers.values()),
                            top_payload=Counter({}).most_common()))
            totals=Counter()
            for q in crossings:totals[q[3]]+=q[2]
            cut[-1]['top_payload']=totals.most_common(6)
        blockers=[]
        for name,box in m['placement'].items():
            overlap=max(0,min(x+width,box['x']+box['w'])-max(x,box['x']))*max(0,min(y+width,box['y']+box['h'])-max(y,box['y']))
            if overlap: blockers.append((name,round(overlap,1)))
        result.append(dict(origin=[x,y],window_um=width,current_model_booked_um2=demand,
                           cell_capacity_at_50pct_um2=capacity,model_ratio=ratio,
                           current_sites=len(near),site_area_um2=sum(q[1] for q in near),
                           top_site_demand=[dict(driver=k[0],kind=k[1],area_um2=round(v,1)) for k,v in attrib.most_common(8)],
                           blocking_outlines=sorted(blockers,key=lambda q:-q[1])[:6],full_die_flow_cuts=cut))
    doc=dict(scope=__doc__,inputs={key:hashlib.sha256(Path(getattr(a,key)).read_bytes()).hexdigest() for key in ('stations','manifest','report')},
             die_um=[W,H],windows=result,interior_centroids=badpins,
             qualification='MODEL_ONLY; no GRT/STA/native/real-PDN result; no blanket channel enlargement inferred')
    Path(a.out).write_text(json.dumps(doc,indent=1)+'\n')
    print('CORRIDOR_MODEL windows',len(result),'interior_centroids',len(badpins),'out',a.out)


if __name__=='__main__':main()
