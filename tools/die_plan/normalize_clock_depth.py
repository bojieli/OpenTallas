#!/usr/bin/env python3
"""Normalize active clock-tree depth with real BUFx24 cells in native islands.

Every inserted clock cell has a physical site and modeled wires. No electrical
wire padding or data-pipeline cycles are added. Scope is an opt-in prototype.
"""
import argparse
from collections import defaultdict
from functools import lru_cache
import json
import math
from pathlib import Path
import die_clock as DC
import schema as S


def depths(T):
    children=defaultdict(list)
    for n in T.nets:
        children[n['drv']].extend(load for _,_,load,_ in n['branches'])
    @lru_cache(None)
    def height(node):
        if node.startswith('port:') and node!='port:root':return 0
        active=[height(c) for c in children.get(node,())];active=[x for x in active if x is not None]
        return 1+max(active) if active else None
    height('port:root')
    return children,height


def normalize(T,tree,P):
    children,height=depths(T);K=DC.KeepIndex(DC.keepouts(P),die=(P.W,P.H))
    occupied=set();sx,sy=.054,.27;width=1.62;ns=30
    for c in T.cells.values():
        for iy in range(math.floor(c['y']/sy),math.ceil((c['y']+.27)/sy)):
            occupied.update((iy,ix) for ix in range(math.floor(c['x']/sx),math.ceil((c['x']+width)/sx)))
    def island(a):
        bx,by=round(a[0]/sx),round(a[1]/sy)
        for ring in range(1,101):
            for dx,dy in sorted([(dx,dy) for dx in range(-ring,ring+1) for dy in range(-ring,ring+1) if max(abs(dx),abs(dy))==ring],key=lambda d:abs(d[0])*width+abs(d[1])*sy):
                ix,iy=bx+dx*ns,by+dy;x,y=ix*sx,iy*sy
                if x<1 or y<1 or x+width>P.W-1 or y+.27>P.H-1:continue
                if any((iy,j) in occupied for j in range(ix,ix+ns)):continue
                if any(K.hit(a,b) for a,b in [(x,y),(x+width,y),(x,y+.27),(x+width,y+.27),(x+width/2,y+.135)]):continue
                occupied.update((iy,j) for j in range(ix,ix+ns));return round(x,6),round(y,6)
        raise ValueError('no native normalization island site')
    ports={'port:'+t['port']:tuple(t['xy']) for t in tree['taps']};ports['port:root']=tuple(tree['meta']['root_um'])
    def xy(node):return ports[node] if node.startswith('port:') else (T.cells[node]['x'],T.cells[node]['y'])
    def branch(a,b,load,layer):
        g=abs(a[0]-b[0])+abs(a[1]-b[1]);bend=(b[0],a[1]) if layer=='M8' else (a[0],b[1])
        return (g,layer,load,g),[a,bend,b]
    result=[];count=0;max_island=0.;edge_counts=[]
    for old in T.nets:
        active=[height(c) for c in children[old['drv']] if height(c) is not None]
        target=max(active) if active else 0
        net={**old,'branches':[],'routes':[]};a=xy(old['drv']);newnets=[]
        for _,layer,load,_ in old['branches']:
            depth=height(load);extra=target-depth if depth is not None else 0
            names=[]
            for j in range(extra):
                n=f'nnorm{count}';count+=1;x,y=island(a);T.cell(n,x,y,'normalize',None);names.append(n)
                max_island=max(max_island,abs(x-a[0])+abs(y-a[1]))
            first=names[0] if names else load;b=xy(first);br,route=branch(a,b,first,layer)
            net['branches'].append(br);net['routes'].append(route)
            if names:
                edge_counts.append(extra)
                for j,name in enumerate(names):
                    nxt=names[j+1] if j+1<len(names) else load;br,route=branch(xy(name),xy(nxt),nxt,layer)
                    public=load[5:] if nxt==load and load.startswith('port:') else 'w_'+name
                    newnets.append(dict(name=public,drv=name,branches=[br],routes=[route]))
                if load.startswith('port:'):
                    if len(old['branches'])!=1:raise ValueError('public port net has multiple branches')
                    net['name']='w_pre_'+old['name']
        result.append(net);result.extend(newnets)
    T.nets=result
    incoming={load:n['drv'] for n in T.nets for _,_,load,_ in n['branches']}
    @lru_cache(None)
    def path(node):
        if node=='port:root':return []
        src=incoming[node];return path(src)+([] if node.startswith('port:') else [node])
    for t in tree['taps']:t['path']=path('port:'+t['port']);t['pad_nets']=[]
    for name,node in tree['nodes'].items():node['path']=path(name)
    lengths=[len(t['path']) for t in tree['taps']]
    if min(lengths)!=max(lengths):raise ValueError('depth normalization failed')
    tree['meta'].update(cells=len(T.cells),wire_um=round(sum(L for n in T.nets for L,*_ in n['branches']),3),padding_um=0.,pad_um=0.,pads=0,
        physical_depth_normalization=dict(added_clock_cells=count,clock_stages_per_tap=lengths[0],data_cycles_added=0,
            max_island_displacement_um=round(max_island,3),max_inserted_chain=max(edge_counts,default=0),
            inserted_clock_area_um2=round(count*1.62*.27,4),site_um=[sx,sy],hidden_wire_pad_um=0))
    return T,tree

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('source',type=Path);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();T=DC.load_tree(a.source);tree=json.loads((a.source/'tree.json').read_text())
    T,tree=normalize(T,tree,S.Plan(S.load(a.plan)));a.out.mkdir(parents=True,exist_ok=True)
    DC.NDR_MODE='4w';DC.WIDE_LEVELS=6
    DC.write_verilog(T,a.out/'ctree.v');DC.write_spef(T,a.out/'ctree.spef')
    for name,obj in [('tree.json',tree),('place.json',T.cells),('nets.json',dict(ports=T.ports,nets=T.nets))]:(a.out/name).write_text(json.dumps(obj))
    print(json.dumps(tree['meta']['physical_depth_normalization'],indent=2))
