#!/usr/bin/env python3
"""Write explicit DIAGNOSTIC all-cell allocation from a declared owner policy."""
import argparse,hashlib,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--inventory',required=True);p.add_argument('--width',type=float,required=True);p.add_argument('--height',type=float,required=True);p.add_argument('--root-width',type=float,required=True);p.add_argument('--root-height',type=float,required=True);p.add_argument('--root-if-cells',type=int,required=True);p.add_argument('--max-anchor-displacement',type=float);p.add_argument('--site-pitch',type=float,required=True);p.add_argument('--row-pitch',type=float,required=True);p.add_argument('--row-origin-x',type=float,required=True);p.add_argument('--row-origin-y',type=float,required=True);p.add_argument('--policy-owner',required=True);p.add_argument('--out',required=True);a=p.parse_args();raw=Path(a.inventory).read_bytes();x=json.loads(raw);st=[]
for s in x['stages']:
 r=s['provisional_ff_rect_um'];w,h=(a.root_width,a.root_height) if s['cells']>=a.root_if_cells else(a.width,a.height);cx,cy=(r[0]+r[2])/2,(r[1]+r[3])/2
 if r[2]-r[0]>w or r[3]-r[1]>h:raise ValueError('declared window cannot hold legacy FF envelope '+s['stage'])
 z=dict(stage=s['stage'],windows_um=[[cx-w/2,cy-h/2,cx+w/2,cy+h/2]],max_cells=s['cells'],max_area_um2=s['mapped_area_um2']+1e-8,legacy_ff_rect_um=r,node_xy_um=s['node_xy_um'])
 if a.max_anchor_displacement is not None:z['max_anchor_displacement_um']=a.max_anchor_displacement
 st.append(z)
b=dict(schema='ot_provider_placement_budget/1',inventory_sha256=hashlib.sha256(raw).hexdigest(),diagnostic_only=True,policy_owner=a.policy_owner,all_cell_count=x['counts']['cells'],all_cell_area_um2=x['counts']['mapped_area_um2'],row_grid_um=dict(origin=[a.row_origin_x,a.row_origin_y],site_pitch=a.site_pitch,row_pitch=a.row_pitch,orient='R0'),stages=st)
Path(a.out).write_text(json.dumps(b,separators=(',',':'))+'\n');print(json.dumps(dict(stages=len(st),allcells=b['all_cell_count'],area_um2=b['all_cell_area_um2'],diagnostic_only=True,policy_owner=a.policy_owner)))
