"""Replan only contact groups affected by two moved FFs and the diagnosed seam rail.
Retain every other accepted conductor; bounded contexts cover all candidate stacks
and the planner's three nearest full-grid M9 destinations. No geometry waiver.
"""
import json,shutil
from pathlib import Path
Q=Path('/srv/opentallas-scratch2/claude');R=Q/'codex-qc-import-0824';F=R/'reachfix';o=F/'incremental_pg';o.mkdir(exist_ok=True)
old=json.load(open(R/'fullpg/access_plan.json'));rr=json.load(open(R/'fullpg/reserved_access.json'));assert len(rr)==27*len(old['paths']) and len(old['vias_dbu'])==8*len(old['paths'])
moved={'start_provider/'+q['inst'] for q in json.load(open(F/'fix.json'))['moved']};redo={(m,p['net']) for p in old['failed'] for m in p['members']};removed=[];retained=[];rois=[]
for j,p in enumerate(old['paths']):
 if moved.intersection(p['members']):removed.append(j);redo.update((m,p['net']) for m in p['members'])
 else:retained.append(j)
t=json.load(open(F/'readback/power_terms.json'));t['terms']=[q for q in t['terms'] if (q['inst'],q['pin']) in redo];assert len(t['terms'])==len(redo)
for q in t['terms']:
 for ly,x0,y0,x1,y1 in q['shapes_dbu']:rois.append([x0-80000,y0-3000,x1+80000,y1+3000])
def hit(r):return any(r[0]<z[2] and z[0]<r[2] and r[1]<z[3] and z[1]<r[3] for z in rois)
g=json.load(open(F/'readback/geometry.json'))
for key,skip in [('obstructions',2),('signal_shapes',3),('existing_supplies',2)]:g[key]=[q for q in g[key] if hit(q[skip:])]
g['cells']=[];json.dump(g,open(o/'geometry.json','w'),separators=(',',':'));json.dump(t,open(o/'power_terms.json','w'),separators=(',',':'))
e=json.load(open(F/'readback/endpoints.json'));e['endpoints']={n:q for n,q in e['endpoints'].items() if hit([round(v*1000) for v in q['rect_um']])};json.dump(e,open(o/'endpoints.json','w'),separators=(',',':'))
for name in ['pg_rects.json','probe_census.json']:shutil.copyfile(F/'readback'/name,o/name)
def select(data):return [q for q in data if hit([round(v*1000) for v in q[2:]])]
json.dump(select(json.load(open(R/'clock_seed.json'))),open(o/'clock_seed.json','w'),separators=(',',':'));json.dump(select(json.load(open(R/'clock_landing_reserved.json'))),open(o/'joint_clock_reserved.json','w'),separators=(',',':'))
pw=select([r for j in retained for r in rr[27*j:27*j+27]])+select(json.load(open(R/'nativepg/bridges/reserved_bridges.json')));json.dump(pw,open(o/'reserved_power.json','w'),separators=(',',':'))
meta=dict(removed_groups=removed,retained_groups=len(retained),replanned_contacts=len(redo),redone=sorted(redo),rois_dbu=rois,source=g['source'],scope='Bounded incremental construction; all other accepted PG paths immutable; does not yet reserve qualified new provider clock escapes')
json.dump(meta,open(o/'context.json','w'),indent=2);print(json.dumps({k:v for k,v in meta.items() if k not in ['rois_dbu','redone']},indent=2),flush=True)
