#!/usr/bin/env python3
"""Translate existing current KV hard-frame shore groups; geometric candidate only."""
import argparse,hashlib,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
m=json.loads(a.source.read_text());groups={'W':[],'E':[],'C':[]}
for i in m['insts']:
    if i['m'].startswith('qkd_') or i['m']=='ot_hbm3e_phy':
        side='W' if i['x']+i['w']<=3821.905 else 'E' if i['x']>=27963.791 else 'C'
        groups[side].append(i)
bounds={s:[min(i['x'] for i in g),min(i['y'] for i in g),max(i['x']+i['w'] for i in g),max(i['y']+i['h'] for i in g)] for s,g in groups.items()}
margin,channel,cw=21.6,259.2,2320.056
ww,ew=bounds['W'][2]-bounds['W'][0],bounds['E'][2]-bounds['E'][0]
cx=margin+ww+channel;ex=cx+cw+channel
height=max(bounds[s][3]-bounds[s][1] for s in ('W','E'))+2*margin
width=ex+ew+margin
rects=[]
for side,ins in groups.items():
    x0=margin if side=='W' else ex if side=='E' else cx+(cw-(bounds[side][2]-bounds[side][0]))/2
    dy=margin-bounds[side][1] if side!='C' else 0
    for i in ins:
        q=dict(i);q['x']+=x0-bounds[side][0];q['y']+=dy;rects.append(q)
rects += [dict(n='system_host_phy_allowance',m='ot_qfd_serdes_112g_x12_phy_request',x=cx,y=margin,w=cw,h=1563.57),
    dict(n='host_transport_allowance',m='RESERVED_UNIMPLEMENTED',x=cx,y=margin+1563.57+channel,w=cw,h=600.),
    dict(n='d2d_phy_reference',m='ot_qkvd_ucie_x64_phy_REFERENCE',x=cx,y=height-margin-777.6,w=777.6,h=777.6),
    dict(n='d2d_adapter_reference',m='ot_qkvd_kv_end_REFERENCE',x=cx,y=height-margin-777.6-channel-518.4,w=777.6,h=518.4)]
overlap=[]
for j,i in enumerate(rects):
 for q in rects[j+1:]:
  if i['x']<q['x']+q['w']-1e-6 and q['x']<i['x']+i['w']-1e-6 and i['y']<q['y']+q['h']-1e-6 and q['y']<i['y']+i['h']-1e-6:overlap.append([i['n'],q['n']])
outside=[i['n'] for i in rects if min(i['x'],i['y'])<0 or i['x']+i['w']>width+1e-6 or i['y']+i['h']>height+1e-6]
r=dict(status='GEOMETRIC_TRANSLATION_ONLY_NOT_ADOPTED',source=dict(path=str(a.source),sha256=hashlib.sha256(a.source.read_bytes()).hexdigest()),
    die_um=[width,height],area_mm2=width*height/1e6,overlaps=overlap,outside=outside,source_group_bounds=bounds,positions=rects,
    missing=['Current 96 ECTL subleaf expansion and all parent clocks/pins must bind.','All translation origins must be legalized for signal and PG phase; affine placement alone does not satisfy phase.','All shore-to-center relay/reset/clock wiring must be regenerated, including actual-pin cuts and timing.','Host and adapter reservations are provisional/reference only, not completed physical views.','Package HBM and die-to-die PHY compatibility and TP8 native transport cycles remain unverified.'])
a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ('positions','source_group_bounds','missing')},indent=2))
