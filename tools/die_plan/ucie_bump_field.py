#!/usr/bin/env python3
"""Prototype extra PG at vacant45um sites, retaining a published UCIe16-column bump template.

This is a bump/PG feasibility model, not a vendor PHY or electrical qualification.
The16-column reference's recommended pitch is25-37um;45um uses more shoreline.
"""
import argparse,json,math
from pathlib import Path

def build(template,rect,pitch=45.):
    if (template['map_columns'],template['map_rows'])!=(16,30):raise ValueError('expected the complete16x30publishedtemplate')
    x0,y0,x1,y1=rect;w,h=x1-x0,y1-y0;dx=math.sqrt(3)*pitch/2;dy=pitch/2
    # Rigid embedding; no per-signal move or geometry distortion.
    ox=x0+w/2-7*dx;oy=y0+h/2-14*dy
    edge=pitch/2
    c0=math.ceil((x0+edge-ox)/dx-1e-9);c1=math.floor((x1-edge-ox)/dx+1e-9)
    r0=math.ceil((y0+edge-oy)/dy-1e-9);r1=math.floor((y1-edge-oy)/dy+1e-9)
    field={(r,c):(round(ox+c*dx,6),round(oy+r*dy,6))for r in range(r0,r1+1)for c in range(c0,c1+1)if(r+c)%2==0}
    original={};sites={}
    for q in template['points']:
        key=q['row'],q['col'];n=q['name']
        if key in original or key not in field:raise ValueError('published site duplicate or outside reservedfield')
        role='GND'if n=='vss'else'POWER'if n in {'vccio','vccfwdio'}else'SIGNAL'
        original[key]=(n,role)
        sites[key]=dict(name=n,role=role,published=True,row=key[0],col=key[1],xy_um=field[key])
    if len(original)!=240:raise ValueError('incompletepublishedtemplate')
    signals=[q for q in sites.values()if q['role']=='SIGNAL']
    if len(signals)!=156 or len({q['name']for q in signals})!=156:raise ValueError('lost signal/control positions')
    vacant=set(field)-set(original)
    if len(vacant)!=74:raise ValueError(f'expected74vacantfieldsites, got{len(vacant)}')
    old_power=[q['xy_um']for q in sites.values()if q['role']=='POWER'];new_power=[]
    # Distribute added supply contacts over the vacant perimeter by farthest-point fill.
    free=set(vacant)
    for _ in range(39):
        k=max(sorted(free),key=lambda k:min((field[k][0]-p[0])**2+(field[k][1]-p[1])**2 for p in old_power+new_power))
        free.remove(k);new_power.append(field[k])
        sites[k]=dict(name=f'extra_power_r{k[0]}c{k[1]}',role='POWER',published=False,row=k[0],col=k[1],xy_um=field[k])
    for k in sorted(free):sites[k]=dict(name=f'extra_ground_r{k[0]}c{k[1]}',role='GND',published=False,row=k[0],col=k[1],xy_um=field[k])
    # Fail closed if any old signal/control/ground position was repurposed.
    for key,(name,role)in original.items():
        if sites[key]['name']!=name or sites[key]['role']!=role or sites[key]['xy_um']!=field[key]:raise ValueError('publishedsitechanged')
    counts={k:sum(q['role']==k for q in sites.values())for k in ['POWER','GND','SIGNAL']}
    if counts!={'POWER':79,'GND':79,'SIGNAL':156}:raise ValueError('unexpectedallocation')
    bumps=[('VDD'if q['role']=='POWER'else'VSS',*q['xy_um'])for q in sites.values()if q['role']!='SIGNAL']
    return dict(schema='ucie-extra-pg-prototype-v1',source=template['source'],pdf_page=template['pdf_page'],slide=template['slide'],rect_um=rect,pitch_um=pitch,edge_clearance_um=edge,template_columns=16,template_rows=30,template_recommended_pitch_um=[25,37],counts=counts,original_sites=len(original),vacant_sites_used=len(vacant),added_power=39,added_ground=35,pg_fraction=(counts['POWER']+counts['GND'])/len(field),published_positions_preserved=True,sites=[sites[k]for k in sorted(sites)],bumps=bumps,assumptions=['Published 16-column row/column template instantiated rigidly at 45 um; outside the 25-37 um shoreline optimum','No signal, control, original ground or original supply site moves; only 74 vacant sites gain PG','32 GT/s, 0.6 pJ/b, 0.7 V and the current window stay unchanged; no vendor electrical qualification','SER.SIG_GND is scoped to board SerDes per coordinator; this prototype retains every published UCIe ground and adds 35'])

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--template',required=True);ap.add_argument('--rect',type=float,nargs=4,required=True);ap.add_argument('--out',required=True);a=ap.parse_args();d=build(json.loads(Path(a.template).read_text()),a.rect);Path(a.out).write_text(json.dumps(d,indent=1)+'\n');print(json.dumps({k:v for k,v in d.items()if k not in {'sites','bumps'}},indent=1))
if __name__=='__main__':main()
