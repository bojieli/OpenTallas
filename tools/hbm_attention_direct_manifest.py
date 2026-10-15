#!/usr/bin/env python3
"""Export source-bound attention child pins and OBS for die direct expansion.

Coordinates are the component candidate, not an assigned die placement. All
LEF rectangles (including PG) survive, transformed by the actual orientation.
"""
import argparse, hashlib, json, re
from pathlib import Path

def point(x,y,w,h,o):
    if o == 'R0': return x,y
    if o == 'MX': return x,h-y
    if o == 'MY': return w-x,y
    if o == 'R180': return w-x,h-y
    raise ValueError('unsupported orientation '+o)

def rects(body,w,h,o,xy):
    layer=None; out=[]
    for m in re.finditer(r'\bLAYER\s+(\S+)\s*;|\bRECT\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s*;',body):
        if m.group(1): layer=m.group(1); continue
        if layer is None: raise ValueError('RECT without layer')
        x0,y0,x1,y1=map(float,m.groups()[1:]); a=point(x0,y0,w,h,o); b=point(x1,y1,w,h,o)
        out.append({'layer':layer,'rect_um':[round(min(a[0],b[0])+xy[0],6),round(min(a[1],b[1])+xy[1],6),round(max(a[0],b[0])+xy[0],6),round(max(a[1],b[1])+xy[1],6)]})
    return out

def export(component,root):
    data=json.loads(component.read_text()); children=[]
    for row in data['children']:
        path=root/row['view_lef']; raw=path.read_bytes(); sha=hashlib.sha256(raw).hexdigest()
        if sha != row['sha256'][path.name]: raise ValueError('source LEF hash mismatch: '+str(path))
        text=raw.decode(); w,h=row['w_um'],row['h_um']; o=row['orientation']; xy=row['xy_um']; pins={}
        for m in re.finditer(r'\bPIN\s+(\S+)\s*\n(.*?)\n\s*END\s+\1\s*(?:\n|$)',text,re.S):
            name,body=m.groups(); direction=re.search(r'\bDIRECTION\s+(\w+)',body); use=re.search(r'\bUSE\s+(\w+)',body)
            pins[name]={'direction':direction.group(1) if direction else None,'use':use.group(1) if use else None,'shapes':rects(body,w,h,o,xy)}
        declared=re.findall(r'^\s*PIN\s+(\S+)\s*$',text,re.M)
        if set(declared)!=set(pins): raise ValueError('lost LEF pins: '+str(path))
        obs=re.search(r'^\s*OBS\s*\n(.*?)^\s*END\s*$',text,re.M|re.S)
        children.append({'instance':row['instance'],'master':row['logical_module'],'xy_um':xy,'orientation':o,'outline_um':[w,h],'view_lef':row['view_lef'],'view_lef_sha256':sha,'source_commit':row['source_commit'],'pins':pins,'obs':rects(obs.group(1),w,h,o,xy) if obs else []})
    return {'schema':'opentallas.attention.direct_expansion_manifest.v1','component':data['component'],'component_source_commit':data['source_commit'],'component_sha256':hashlib.sha256(component.read_bytes()).hexdigest(),'assigned_die_placement':False,'repartition_applied':bool(data.get('repartition_request',{}).get('changes')),'scope':'exact candidate component geometry; die lead must assign placement and clocks','outline_um':data['outline_um'],'boundary_ports':data['boundary_ports'],'connections':data['connections'],'boundary_binding':data['boundary_binding'],'children':children}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('component',type=Path);p.add_argument('--root',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
    result=export(a.component,a.root);a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=1)+'\n')
    print(f"{result['component']}: {len(result['children'])} children, {sum(len(c['pins']) for c in result['children'])} pins, {sum(len(c['obs']) for c in result['children'])} OBS rectangles")
