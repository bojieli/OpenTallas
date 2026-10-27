#!/usr/bin/env python3
"""Compose independent axis solutions and check the resulting 2-D core geometry
and the FULL in-core driver-site sets, including empty instances and orientations.
This is a PLAN CANDIDATE only: pin/connection/station regeneration remains required.
"""
import json,sys,itertools,collections
from pathlib import Path
D,T,OUT=sys.argv[1:4];D=Path(D);OUT=Path(OUT);OUT.mkdir(parents=True,exist_ok=True);sys.path.insert(0,T)
import schema as S
raw=json.load(open(D/'r9/plan.json'));M=json.load(open(D/'r9/mesh.json'))
changes=[]
for fam in ('pv','hg','pc'):
 for axis in ('x','y'):
  sol=json.load(open(D/f'{fam}_{axis}.json'));assert sol['status']=='sat',sol
  a='xy'.index(axis)
  for v in sol['placements']:
   t=raw['partition_types'][v['type']];cc={h['inst']:h for h in t['hard_cores']}
   for n in v['cores']:
    hc=cc[n];old=hc.get('orient','R0');fx=old in ('MY','R180');fy=old in ('MX','R180')
    if a==0:fx=v['flip']
    else:fy=v['flip']
    hc['origin_um'][a]=v['new'];hc['orient']={(False,False):'R0',(True,False):'MY',(False,True):'MX',(True,True):'R180'}[(fx,fy)]
    changes.append([v['type'],n,axis,v['old'],v['new'],v['flip']])
# R8's draft annotation is outside the schema; retain it in the candidate receipt.
annotations=raw.pop('plan_deltas',None)
P=S.Plan(raw);errs=S.validate(raw);over=[];outside=[]
for tn,t in P.types.items():
 cs=t.get('hard_cores',[]);w,h=t['outline_um']
 for c in cs:
  x,y=c['origin_um'];cw,ch=c['outline_um']
  if x<0 or y<0 or x+cw>w+1e-6 or y+ch>h+1e-6:outside.append((tn,c['inst']))
 for a,b in itertools.combinations(cs,2):
  ax,ay=a['origin_um'];aw,ah=a['outline_um'];bx,by=b['origin_um'];bw,bh=b['outline_um']
  if ax<bx+bw-1e-6 and bx<ax+aw-1e-6 and ay<by+bh-1e-6 and by<ay+ah-1e-6:over.append((tn,a['inst'],b['inst']))
def census(field):
 mod=collections.defaultdict(list)
 for pn,p in P.parts.items():
  t=P.types[p['type']];points=[P.to_type(pn,d[field]) for d in M['drivers'].values()]
  for c in t.get('hard_cores',[]):
   x,y=c['origin_um'];w,h=c['outline_um'];o=c.get('orient','R0');pts=[]
   for px,py in points:
    if x<px<x+w and y<py<y+h:
     u,v=px-x,py-y
     if o in ('MY','R180'):u=w-u
     if o in ('MX','R180'):v=h-v
     pts.append((round(u*2)/2,round(v*2)/2))
   mod[c['module']].append((pn+'/'+c['inst'],tuple(sorted(set(pts)))))
 res={}
 for m,rows in mod.items():
  sets={s for n,s in rows}
  if any(s for s in sets):res[m]=dict(instances=len(rows),patterns=len(sets),sites_per_instance=sorted({len(s) for s in sets}),examples=[list(s) for s in sorted(sets)[:4]])
 return dict(failing_modules=[m for m,r in res.items() if r['patterns']!=1],by_module=res)
summary=dict(scope='Geometry and driver island feasibility only, not plan adoption',schema_errors=errs,core_overlaps=over,core_outside=outside,changes=len(changes),old_annotations=annotations,ideal_islands=census('ideal'),actual_site_islands=census('site'),remaining='Rebuild driver placement on one canonical per-module island lattice, regenerate core pins/connections/stations and master slices, review, then route. No timing/signoff credit.')
(OUT/'plan.json').write_text(json.dumps(raw,indent=1)+'\n');(OUT/'summary.json').write_text(json.dumps(summary,indent=1)+'\n');(OUT/'changes.json').write_text(json.dumps(changes,indent=1)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k not in ('ideal_islands','actual_site_islands','old_annotations')}));print('ideal FAIL',summary['ideal_islands']['failing_modules']);print('actual FAIL',summary['actual_site_islands']['failing_modules'])
