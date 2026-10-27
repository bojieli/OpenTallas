#!/usr/bin/env python3
"""Faithful width-aware clock RC from native global-route segments and pins.

Wires use ASAP7 platform setRC values with declared 4W(R/4,C*1.3) or
8W(R/8,C*1.6) only on M8/M9. Actual via edges retain their setRC resistance.
Pin terminals attach to the nearest node on their actual pin layer, matching
the global router's on-grid terminal model. Missing/disconnected edges fail.
"""
import argparse
from collections import defaultdict,deque
import json
import math
from pathlib import Path
import re

# ASAP7 ORFS platform setRC.tcl: resistance kohm/um, capacitance fF/um.
WIRE={1:(.0704175,1e-10),2:(.0297127,.174942),3:(.0312870,.155554),4:(.0180365,.178475),5:(.0189935,.164264),6:(.0118796,.187426),7:(.0125096,.162979),8:(.00844765,.103962),9:(.00889556,.0928446)}
VIA={1:.0172,2:.0172,3:.0172,4:.0118,5:.0118,6:.0082,7:.0082,8:.0063}


def read_pins(path):
    nets={};dbu=None
    for line in Path(path).read_text().splitlines():
        f=line.split('\t')
        if f[0]=='DBU':dbu=int(f[1])
        elif f[0]=='NET':nets[f[1]]=dict(rule=f[2],pins=[])
        elif f[0]=='PIN':
            _,net,kind,name,direction,layer,x,y=f
            nets[net]['pins'].append(dict(kind=kind,name=name,direction=direction,point=(round(float(x)),round(float(y)),int(layer[1:]))))
    if not dbu:raise ValueError('pin export lacks DBU')
    return dbu,nets


def read_segments(path):
    nets={};name=None;edges=None
    for raw in Path(path).read_text().splitlines():
        line=raw.strip()
        if not line:continue
        if line=='(':
            if name is None or edges is not None:raise ValueError('malformed segment block')
            edges=[]
        elif line==')':
            if edges is None:raise ValueError('unmatched close')
            if name in nets:raise ValueError(f'duplicate segment net {name}')
            nets[name]=edges;name=None;edges=None
        elif edges is None:name=line
        else:
            f=line.split()
            if len(f)!=6:raise ValueError(f'bad segment: {line}')
            a=(int(f[0]),int(f[1]),int(f[2][1:]));b=(int(f[3]),int(f[4]),int(f[5][1:]))
            if a!=b:edges.append((a,b))
    if name is not None or edges is not None:raise ValueError('incomplete route segment file')
    return nets


def width(rule):
    if re.search(r'8w',rule,re.I):return 8
    if re.search(r'4w',rule,re.I):return 4
    if rule=='DEFAULT':return 1
    raise ValueError(f'undeclared clock NDR {rule}')


def graph(edges,pins,dbu,tolerance_um):
    nodes={p for edge in edges for p in edge};by_line=defaultdict(list)
    for p in nodes:
        by_line[(p[2],'H',p[1])].append(p);by_line[(p[2],'V',p[0])].append(p)
    split=set()
    for a,b in edges:
        if a[2]!=b[2]:
            if a[:2]!=b[:2] or abs(a[2]-b[2])!=1:raise ValueError('invalid/nonadjacent via edge')
            split.add(tuple(sorted((a,b))));continue
        if a[0]!=b[0] and a[1]!=b[1]:raise ValueError('non-Manhattan routed edge')
        axis=0 if a[0]!=b[0] else 1;kind='H' if axis==0 else 'V';fixed=a[1-axis]
        points=sorted((p for p in by_line[(a[2],kind,fixed)] if min(a[axis],b[axis])<=p[axis]<=max(a[axis],b[axis])),key=lambda p:p[axis])
        split.update(tuple(sorted((x,y))) for x,y in zip(points,points[1:]))
    adj=defaultdict(set)
    for a,b in split:adj[a].add(b);adj[b].add(a)
    if not nodes:raise ValueError('empty routed net')
    seen=set();q=[next(iter(nodes))]
    while q:
        p=q.pop()
        if p not in seen:seen.add(p);q.extend(adj[p]-seen)
    if seen!=nodes:raise ValueError('disconnected routed graph (missing segment)')
    attached=[];maximum=0.
    for pin in pins:
        p=pin['point'];candidates=[v for v in nodes if v[2]==p[2]]
        if not candidates:raise ValueError(f'no route on pin layer for {pin["name"]}')
        near=min(candidates,key=lambda v:abs(v[0]-p[0])+abs(v[1]-p[1]))
        distance=(abs(near[0]-p[0])+abs(near[1]-p[1]))/dbu
        if distance>tolerance_um:raise ValueError(f'pin {pin["name"]} is {distance:.3f}um from routed graph')
        attached.append((pin,near));maximum=max(maximum,distance)
    if not any(p['direction']=='O' and p['kind']=='I' or p['direction']=='I' and p['kind']=='P' for p in pins):raise ValueError('no driver pin')
    return sorted(split),attached,maximum


def convert(segments,pinfile,out,design='die_ctree',tolerance_um=20.):
    dbu,nets=read_pins(pinfile);routes=read_segments(segments)
    missing={n for n,v in nets.items() if len(v['pins'])>=2}-set(routes)
    if missing:raise ValueError(f'missing routed clock nets {sorted(missing)[:8]}')
    stats=dict(nets=0,wire_edges=0,via_edges=0,pin_attach_max_um=0.,width_nets=defaultdict(int),clock_only=True)
    with Path(out).open('w') as f:
        f.write(f'*SPEF "IEEE 1481-1998"\n*DESIGN "{design}"\n*DATE "native routed clock graph"\n*VENDOR "OpenTallas"\n*PROGRAM "clock_segments_spef"\n*VERSION "1"\n*DESIGN_FLOW "NAME_SCOPE LOCAL"\n*DIVIDER /\n*DELIMITER :\n*BUS_DELIMITER [ ]\n*T_UNIT 1 PS\n*C_UNIT 1 FF\n*R_UNIT 1 KOHM\n*L_UNIT 1 HENRY\n\n')
        for name,edges in routes.items():
            if name not in nets:raise ValueError(f'route lacks pin identity {name}')
            info=nets[name];w=width(info['rule']);edges,attached,attach=graph(edges,info['pins'],dbu,tolerance_um)
            caps=defaultdict(float);res=[];nodes=sorted({p for edge in edges for p in edge});nodeids={p:f'{name}:{i+1}' for i,p in enumerate(nodes)}
            for a,b in edges:
                if a[2]!=b[2]:
                    r=VIA[min(a[2],b[2])];stats['via_edges']+=1
                else:
                    L=(abs(a[0]-b[0])+abs(a[1]-b[1]))/dbu;r,c=WIRE[a[2]]
                    if a[2]>=8:
                        r/=w;c*=1.6 if w==8 else 1.3 if w==4 else 1.
                    r*=L;cap=c*L;caps[a]+=cap/2;caps[b]+=cap/2;stats['wire_edges']+=1
                res.append((nodeids[a],nodeids[b],r))
            f.write(f'*D_NET {name} {sum(caps.values()):.9f}\n*CONN\n')
            for p,n in attached:
                f.write(f'*{p["kind"]} {p["name"]} {p["direction"]}\n')
                res.append((p['name'],nodeids[n],1e-9))
            f.write('*CAP\n')
            for i,(p,c) in enumerate(sorted(caps.items()),1):f.write(f'{i} {nodeids[p]} {c:.9f}\n')
            f.write('*RES\n')
            for i,(a,b,r) in enumerate(res,1):f.write(f'{i} {a} {b} {r:.12f}\n')
            f.write('*END\n\n');stats['nets']+=1;stats['width_nets'][str(w)]+=1;stats['pin_attach_max_um']=max(stats['pin_attach_max_um'],attach)
    stats['width_nets']=dict(stats['width_nets']);return stats

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('segments',type=Path);p.add_argument('pins',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--design',default='die_ctree');p.add_argument('--pin-tolerance-um',type=float,default=20.)
    a=p.parse_args();print(json.dumps(convert(a.segments,a.pins,a.out,a.design,a.pin_tolerance_um),indent=2))
