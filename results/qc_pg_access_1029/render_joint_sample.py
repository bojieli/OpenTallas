#!/usr/bin/env python3
import json,argparse
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--plan',required=True);p.add_argument('--old-pg',required=True);p.add_argument('--new-pg',required=True);p.add_argument('--out',required=True);a=p.parse_args()
rr=json.load(open(a.plan))['records'];chosen=[];seen=set()
for r in rr:
 if r['cell'] in seen:continue
 chosen.append(r);seen.add(r['cell'])
 if len(chosen)==4:break
panels=[]
for r in chosen:
 x,y=r['entry_xy_um'];panels.append(dict(cell=r['cell'],box=[x-2,y-1.6,x+2,y+1.6],clock=[q for rec in rr if abs(rec['entry_xy_um'][0]-x)<4 and abs(rec['entry_xy_um'][1]-y)<4 for q in rec['geometry']+[[rec['net'],'M8',rec['backbone_xy_um'][0]-.096,rec['m8_witness_y_um']-.04,rec['backbone_xy_um'][0]+.096,rec['m8_witness_y_um']+.04]]]))
for mode,f in [('old',a.old_pg),('new',a.new_pg)]:
 rows=json.load(open(f))
 for v in panels:
  x0,y0,x1,y1=v['box'];v[mode]=[r for r in rows if r[1]=='M8' and r[2]<x1 and r[4]>x0 and r[3]<y1 and r[5]>y0]
 del rows
json.dump(panels,open(a.out,'w'))
