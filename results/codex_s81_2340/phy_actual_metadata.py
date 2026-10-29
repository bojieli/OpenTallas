#!/usr/bin/env python3
"""Reconcile stale ES0/ES1 IO/PG metadata to actual typed PHY placement. Domain/grid unchanged; shoreline remains FAIL."""
import json,sys,copy
from pathlib import Path
sys.path.insert(0,'tools/die_plan')
import schema as S,die_io as IO,check as C
raw=json.load(open(sys.argv[1]));p=S.Plan(raw);records=[]
for part in ('lk_ES0','lk_ES1'):
 t=p.ptype(part);u=next(c for c in t['contents'] if c['inst']=='u_phy');x,y=u['origin_um'];w,h=u['outline_um']
 a=p.to_die(part,(x,y));b=p.to_die(part,(x+w,y+h));box=[round(min(a[0],b[0]),6),round(min(a[1],b[1]),6),round(max(a[0],b[0]),6),round(max(a[1],b[1]),6)]
 d=next(d for d in raw['die']['pg']['domains'] if d['name']=='phy_'+part);io=next(z for z in raw['die']['io'] if z['part']==part and z['iface']=='serdes');before=dict(domain=copy.deepcopy(d),io=copy.deepcopy(io))
 # Existing PG domain already matches the REAL typed macro+guard; do not move clock keepouts/grid.
 dr=d['rect_um'];assert box[0]>=dr[0]-1e-6 and box[1]>=dr[1]-1e-6 and box[2]<=dr[2]+1e-6 and box[3]<=dr[3]+1e-6
 d['phy_macro_um']=box;d['bumps']['rect_um']=box
 # Type is MY: complement of its N/E-side PHY domain = full left strip + lower right strip.
 r=p.rect(part);d['core_strip_um']=[[r[0],r[1],dr[0],r[3]],[dr[0],r[1],r[2],dr[1]]]
 assert all(q[2]>=q[0] and q[3]>=q[1] for q in d['core_strip_um'])
 io['rect_um']=box;io['sites']=IO.count_sites(box,io['pitch_um'],io.get('bump_exclude_um',()))
 note='; CODEX actual-source reconciliation: type.contents u_phy is at local[63.64,302.4], transformed through actualMY placement; prior IO/macro/bump/corestrip metadata stale. PGdomain/grid/typedgeometry/clockkeepouts unchanged. Actual406.08um shoreline exceeds200um rule: structural PHY relocation still REQUIRED, no route/IR/freeze claim.'
 d['note']+=note;io['note']+=note
 records.append(dict(part=part,type=p.parts[part]['type'],typed_phy=copy.deepcopy(u),before=before,after=dict(domain=copy.deepcopy(d),io=copy.deepcopy(io)),edge_distance_um=IO.edge_dist(p,box)))
np=S.Plan(raw);r=C.Report(completeness=True);ios=IO.check(np,r);pgs=IO.check_pg_domains(np,r)
rec=dict(records=records,focused_errors=r.errors(),focused_summary=dict(io=ios,pg=pgs),no_typed_geometry_or_clock_or_latency_change=True)
json.dump(raw,open(sys.argv[2],'w'),indent=1);json.dump(rec,open(sys.argv[3],'w'),indent=2)
print(json.dumps(dict(focused_errors=r.errors(),edge_distance_um=[x['edge_distance_um'] for x in records])))
