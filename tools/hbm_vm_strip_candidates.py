#!/usr/bin/env python3
"""Source-bound bank/LG strip alternatives with exact closed-LEF pin geometry.

Every origin and PG endpoint is a REQUEST. Actual source PG body/pins, clock
routing, channel cuts and native STA remain prerequisites; no virtual body is
substituted for a real SU/SFU/HC unit.
"""
import csv
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/arch/hbm_vm_stageclocks_1103'
LEF='physical/ref_tile/vm_lg_bank_hc_static_1015/views/ot_hbm_vm_lg_static_bank/ot_hbm_vm_lg_static_bank.lef'
W,H,G=150.336,151.2,20.0

def snap(x):return math.ceil(x/2.16)*2.16

def pins(text,stem,face):
    r={}
    for m in re.finditer(r'\n  PIN (\S+)\n(.*?)\n  END \1',text,re.S):
        name=m[1]
        if not name.startswith(stem) or name.split('[')[0] in ('local_read','local_write'):continue
        rs=[tuple(map(float,x)) for x in re.findall(r'RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)',m[2])]
        if not rs:continue
        edge=(min(x[0] for x in rs) if face=='W' else max(x[2] for x in rs) if face=='E' else min(x[1] for x in rs))
        if face=='W':rs=[x for x in rs if abs(x[0]-edge)<1e-6]
        elif face=='E':rs=[x for x in rs if abs(x[2]-edge)<1e-6]
        else:rs=[x for x in rs if abs(x[1]-edge)<1e-6]
        z=min(rs,key=lambda a:(a[2]-a[0])*(a[3]-a[1]));r[name]=[(z[0]+z[2])/2,(z[1]+z[3])/2]
    return r

def inside(x,y,r):return r['x']<x<r['x']+r['w'] and r['y']<y<r['y']+r['h']
def distance(a,b):return abs(a[0]-b[0])+abs(a[1]-b[1])
def main():
    raw=subprocess.check_output(['git','-C',str(ROOT),'show','HEAD:'+LEF]);text=raw.decode()
    local=pins(text,'local_', 'S');near=pins(text,'near_', 'E');far=pins(text,'far_','W')
    assert len(local)==556 and len(near)==556 and len(far)==556,(len(local),len(near),len(far))
    rq=json.loads((OUT/'slot_request.json').read_text());shapes={r['quadrant']:r for r in rq['bank_requests']}
    fp=json.loads(subprocess.check_output(['git','-C',str(ROOT),'show','HEAD:results/arch/hbm_globalfp_1015/noatt/pins/T_band2__npg4_s5.pins.json']))
    result=dict(schema='opentallas.hbm.vm-functional-strip-candidates.v1',state='All homes/PG points REQUESTED. No inherited physical source/body/native qualification.',LG_pin_LEF=dict(file=LEF,sha256=hashlib.sha256(raw).hexdigest(),actual_pin_count_each_face=556,local_S_x_span_um=[min(x[0] for x in local.values()),max(x[0] for x in local.values())]),bank_sources='Four explicit six-root source wrappers from slot_request.json; noATT NE RG5WG2; same-bank pair NPG4 mapping0x33221100 preserved',alternatives={})
    table=[]
    for kind in ('A_straight8','B_staggered_pairs'):
        alt=dict(quadrants={},LG_local_S_reach=[],bank_LG_requested_pin_reach=[],LG_chain_reach=[],limitations=['Only existing actual HC18/15 LEF pin geometry is measured. SU10/7,SFU14/11 require distinct exact physical masters/gates.','No actual SU/SFU/HC body is drawn or qualified; 16nonuniform SU slices and34.752mm2 body remain root-owned.','Every incident nonLG group keeps its semantic window; relocated peer pins/cuts/clocks/reset are OPEN.','Adjacent strip geometry does not establish full native reach, PG access, or TT/FF.'])
        for q,shape in shapes.items():
            sm=[b for n,b in fp['blocks'].items() if n.startswith('sm_'+q)]
            rows=sorted({round(s['y'],3) for s in sm});gaps=[]
            for lo,hi in zip(rows,rows[1:]):
                bottom=max(s['y']+s['h'] for s in sm if abs(s['y']-lo)<.01)
                if hi>bottom:gaps.append((hi-bottom,bottom,hi))
            _,low,high=max(gaps);band=dict(x=snap(min(s['x'] for s in sm)),y=snap(low+10),w=max(s['x']+s['w'] for s in sm)-snap(min(s['x'] for s in sm)),h=high-snap(low+10)-10)
            bw,bh=shape['outline']['w'],shape['outline']['h'];lg0lo,lg0hi=shape['LG0_W_window_um'];ly=(lg0lo+lg0hi)/2-H/2
            frame=3*(W+G)+bw
            pairw=3*(W+G)+2*bw+G
            totalw=8*frame+7*G if kind=='A_straight8' else 4*pairw+3*40
            totalh=bh if kind=='A_straight8' else bh+G+H
            bx=snap(band['x']+(band['w']-totalw)/2);by=snap(band['y']+band['h']-totalh-20)
            blocks=[];leaves={};banks={}
            for b in range(8):
                if kind=='A_straight8': bankx=bx+b*(frame+G)+3*(W+G);lgy=by+ly;shift=0
                else:
                    pair=b//2;left=bx+pair*(pairw+40);bankx=left+3*(W+G)+(b%2)*(bw+G)
                    lgy=by+ly if b%2==0 else by+bh+G;shift=0 if b%2==0 else 160.0
                bank=dict(name=f'vmb_{q}{b}',x=bankx,y=by,w=bw,h=bh,kind='bank_request',clocks=6);blocks.append(bank);banks[b]=bank
                for stage in range(3):
                    leaf=dict(name=f'lg_{q}_{stage}_b{b}',x=bankx-(stage+1)*(W+G)-shift,y=lgy,w=W,h=H,kind='LG_request',READ_RETURN=10+4*stage,WRITE_RETURN=7+4*stage)
                    leaves[b,stage]=leaf;blocks.append(leaf)
            collisions=[]
            for i,a in enumerate(blocks):
                for b in blocks[i+1:]:
                    dx=min(a['x']+a['w'],b['x']+b['w'])-max(a['x'],b['x']);dy=min(a['y']+a['h'],b['y']+b['h'])-max(a['y'],b['y'])
                    if dx>1e-6 and dy>1e-6:collisions.append([a['name'],b['name'],round(dx*dy,3)])
            assert not collisions,collisions
            outside=[b['name'] for b in blocks if b['x']<band['x'] or b['y']<band['y'] or b['x']+b['w']>band['x']+band['w'] or b['y']+b['h']>band['y']+band['h']]
            assert not outside,outside
            endpoints=[]
            for pg in range(4):
                for stage in range(3):
                    a=leaves[2*pg,stage];b=leaves[2*pg+1,stage]
                    # Naive per-PG midpoint is recorded even if it lands inside a bank.
                    midpoint=[(a['x']+b['x'])/2+W/2,min(a['y'],b['y'])-20]
                    endpoint=midpoint if kind=='A_straight8' else [banks[2*pg]['x']-[20,190,360][stage],min(a['y'],b['y'])-20]
                    blocked=[z['name'] for z in blocks if inside(*endpoint,z)]
                    endpoints.append(dict(pg=pg,stage=stage,x=endpoint[0],y=endpoint[1],kind='PG_endpoint_request',actual_body=None,blocked_by=blocked))
                    for bank,leaf in [(2*pg,a),(2*pg+1,b)]:
                        ds={n:distance([leaf['x']+xy[0],leaf['y']+xy[1]],endpoint) for n,xy in local.items()}
                        row=dict(candidate=kind,quadrant=q,pg=pg,stage=stage,bank=bank,leaf=leaf['name'],local_S_x_min=leaf['x']+min(x[0] for x in local.values()),local_S_x_max=leaf['x']+max(x[0] for x in local.values()),local_S_y=leaf['y'],requested_PG_x=endpoint[0],requested_PG_y=endpoint[1],worst_pin=max(ds,key=ds.get),max_pin_to_requested_endpoint_um=round(max(ds.values()),3),margin_to500_um=round(500-max(ds.values()),3),endpoint_obstructed=bool(blocked),scope='ActualLGLEF pin to REQUESTED point; source PG actual pins/body required')
                        alt['LG_local_S_reach'].append(row);table.append(row)
            for bank in range(8):
                for stage in (1,2):
                    a=leaves[bank,stage];b=leaves[bank,stage-1];ds={}
                    for name,xy in near.items():
                        target=name.replace('near_','far_',1);other=far[target]
                        ds[name]=distance([a['x']+xy[0],a['y']+xy[1]],[b['x']+other[0],b['y']+other[1]])
                    alt['LG_chain_reach'].append(dict(quadrant=q,bank=bank,stage=stage,max_um=round(max(ds.values()),3),worst_pin=max(ds,key=ds.get),scope='HC actual LEF pin geometry at requested LG homes; distinct SU/SFU physical pin shapes remain required'))
            # Exact actual LG nearE pins against the requested future bank-W bit windows.
            for b,bank in banks.items():
                leaf=leaves[b,0];ds={}
                for name,xy in near.items():
                    m=re.match(r'near_(rq|rr|wq|w_done)(?:\[(\d+)\])?$',name);assert m,name
                    base={'rq':'rq0','rr':'rr0','wq':'wq0','w_done':'wq_done0'}[m[1]];index=int(m[2] or 0);width=shape['pin_widths'][base];lo,hi=shape['pin_windows_um'][base]
                    planned=[bank['x'],bank['y']+lo+(index+.5)*(hi-lo)/width]
                    ds[name]=distance([leaf['x']+xy[0],leaf['y']+xy[1]],planned)
                alt['bank_LG_requested_pin_reach'].append(dict(quadrant=q,bank=b,worst_pin=max(ds,key=ds.get),max_um=round(max(ds.values()),3),margin_um=round(500-max(ds.values()),3),scope='ActualLGnearE to requested bankW bit positions; actual bankODB must verify'))
            alt['quadrants'][q]=dict(band=band,strip_bbox=dict(x=bx,y=by,w=totalw,h=totalh),blocks=blocks,PG_endpoint_requests=endpoints,bank_LG_overlap=collisions,band_outside=outside,source_body='OPEN: actual16nonuniform SU slices/other engine body pins and channels must compose into remaining space')
        alt['summary']=dict(max_LG_local_pin_to_requested_point_um=max(z['max_pin_to_requested_endpoint_um'] for z in alt['LG_local_S_reach']),obstructed_endpoint_rows=sum(z['endpoint_obstructed'] for z in alt['LG_local_S_reach']),over500_rows=sum(z['max_pin_to_requested_endpoint_um']>500 for z in alt['LG_local_S_reach']),max_actual_LG_to_requested_bank_um=max(z['max_um'] for z in alt['bank_LG_requested_pin_reach']),bank_LG_over500=sum(z['max_um']>500 for z in alt['bank_LG_requested_pin_reach']),max_LG_chain_um=max(z['max_um'] for z in alt['LG_chain_reach']))
        result['alternatives'][kind]=alt
    result['recommendation']='B_staggered_pairs IF actual bank/engine pins, clocks and all incident cuts qualify. A straight-strip midpoint PG points fall inside bank OBS and lack legal body placement; no native claim. B preserves each bank pair and uses row-staggered bank1 LG chains without changing registered transport edges.'
    (OUT/'strip_candidates.json').write_text(json.dumps(result,indent=2)+'\n')
    with (OUT/'LG_local_S_reach.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
    draw(result)
    for k,v in result['alternatives'].items():print(k,v['summary'])

def draw(data):
    scale=.1;svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="580" viewBox="0 0 1400 580">','<rect width="1400" height="580" fill="white"/>','<style>text{font-family:Arial,sans-serif} .label{font-size:9px}</style>']
    for i,(name,alt) in enumerate(data['alternatives'].items()):
        q=alt['quadrants']['SW'];band=q['band'];ox=30;oy=90+i*255
        svg.append(f'<text x="30" y="{oy-45}" font-size="16">{name}: SW actual-source bank/LG requests, same 1.8 mm band</text>')
        svg.append(f'<text x="30" y="{oy-25}" font-size="12">All placements and red PG points are requests. Actual SU/SFU/HC bodies and endpoint pins are OPEN.</text>')
        svg.append(f'<rect x="{ox}" y="{oy}" width="{band["w"]*scale}" height="{band["h"]*scale}" fill="#fafafa" stroke="#999"/>')
        for b in q['blocks']:
            x=ox+(b['x']-band['x'])*scale;y=oy+(band['y']+band['h']-b['y']-b['h'])*scale
            color='#b8d7f4' if b['kind']=='bank_request' else '#bfe5c2'
            svg.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{b["w"]*scale:.2f}" height="{b["h"]*scale:.2f}" fill="{color}" stroke="#444" stroke-width=".5"/>')
            label=b['name'].replace('vmb_SW','B').replace('lg_SW_','L')
            svg.append(f'<text class="label" x="{x+2:.2f}" y="{y+11:.2f}">{label}</text>')
        for p in q['PG_endpoint_requests']:
            x=ox+(p['x']-band['x'])*scale;y=oy+(band['y']+band['h']-p['y'])*scale
            svg.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2.5" fill="#c22"/>')
        svg.append(f'<text x="30" y="{oy+202}" font-size="12">Bank/LG rectangles: no mutual overlap/outside. Actual per-pin reach and endpoint-obstruction counts are in strip_candidates.json.</text>')
    svg.append('</svg>');(OUT/'strip_candidates.svg').write_text('\n'.join(svg))
if __name__=='__main__':main()
