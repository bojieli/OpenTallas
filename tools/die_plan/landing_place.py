"""Fail-closed FIRM placement of actual mapped landing/collector cells."""
from pathlib import Path
from collections import defaultdict
import re


def safe(s):return re.sub(r'\W','_',s)


def tcl(P,tn):
    c=P.types[tn].get('clock',{}).get('landing_contract',{})
    groups=[];status=[];tree=c.get('collector_tree');root=c.get('collector_root_node')
    def near(xy):
        x,y=xy;return [x-2.16,y-2.16,x+2.16,y+2.16]
    for name,band in c.get('bands',{}).items():
        if band.get('placement')=='FAIL' or not band.get('rect_um'):raise ValueError(f'{tn}.{name}: landing band absent')
        groups.append((band.get('instance','u_cland_'+name),band['rect_um'],'ring:'+name))
    for s in c.get('collector_local_sources',[]):
        x,y=s['xy_um']
        for kind in ('ready','fault'):status.append((f'landing_{kind}_'+s['name'],x,y))
        groups.append(('u_cland_rst_'+s['name'],near(tree['relays'][next(i for i,r in enumerate(tree['relays']) if r['q']==f"rst_n_t{s['tap']}")]['xy']),'raw-copy-optional'))
    if root:
        adj=defaultdict(list);xy={'rst_root_n':tree['root']}
        for r in tree['relays']:adj[r['q']].append(r['d']);adj[r['d']].append(r['q']);xy[r['q']]=r['xy']
        parent={root:None};todo=[root]
        while todo:
            n=todo.pop()
            for q in adj[n]:
                if q not in parent:parent[q]=n;todo.append(q)
        sources=[f"rst_n_t{s['tap']}" for s in c.get('collector_local_sources',[])]+[s['node'] for s in c.get('collector_children',[])]
        active=set()
        for n in sources:
            while n is not None:active.add(n);n=parent[n]
        for n in sorted(active):
            groups.append(('u_cland_collect_'+safe(n),near(xy[n]),'collector:'+n))
            if n!='rst_root_n':groups.append(('u_cland_reset_'+safe(n),near(xy[n]),'raw-copy-optional'))
        for s in c.get('collector_children',[]):
            if s['seam']:
                x,y=s['xy_um'];i=s['index']
                status.extend([(f'cland_dn_trained_{i}',x,y),(f'cland_dn_guard_{i}',x,y)])
    out=['set cland_groups {']
    for p,r,tag in groups:
        # Optional raw copies only exist when the original START tap is gated.
        if tag=='raw-copy-optional':continue
        out.append('  {'+p+' {'+' '.join(f'{v:.5f}' for v in r)+'} '+tag+'}')
    out+=['}','set cland_optional_groups {']
    for p,r,tag in groups:
        if tag=='raw-copy-optional':out.append('  {'+p+' {'+' '.join(f'{v:.5f}' for v in r)+'} '+tag+'}')
    out+=['}','set cland_status {']
    out+=['  {'+n+f' {x:.5f} {y:.5f}'+'}' for n,x,y in status]
    out+=['}']
    return '\n'.join(out)+'\n'+Path(__file__).with_name('landing_placement.tcl').read_text()
