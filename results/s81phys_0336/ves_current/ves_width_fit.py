import json,math
from pathlib import Path
D=json.load(open('/home/ubuntu/coord/preview/s81phys0336/unsigned_clock/parent_plan.json'));rows=[]
def bb(c,extra=0):
 x,y=c['origin_um'];dx,dy=c.get('track_offset_um',[0,0]);w,h=c['outline_um'];return[x+dx,y+dy,x+dx+w+extra,y+dy+h]
def sep(a,b):return max(a[0]-b[2],b[0]-a[2],a[1]-b[3],b[1]-a[3])
for tn,t in D['partition_types'].items():
 for c in t.get('hard_cores',[]):
  if c.get('module')!='ot_s81sl_ve_s':continue
  a=bb(c);b=bb(c,8.64);tw,th=t['outline_um'];others=[(sep(b,bb(n)),n['inst'])for n in t.get('hard_cores',[])if n is not c];near=min(others)if others else(None,None);rows.append(dict(type=tn,inst=c['inst'],orient=c.get('orient','R0'),old_box=a,candidate_box=b,contained=b[0]>=0 and b[1]>=0 and b[2]<=tw+1e-6 and b[3]<=th+1e-6,nearest_neighbor=near[1],min_bbox_separation_um=near[0],overlaps=[dict(inst=n['inst'],separation_um=sep(b,bb(n)))for n in t.get('hard_cores',[])if n is not c and sep(b,bb(n))<-1e-6]))
R=dict(scope='READONLY analytic +8.64width estimate only; no plan/source adoption or physical launch. Parent externalpins/outlines/neighbors untouched; internalchildpin worldXY changes need completeG0C.',plan_sha256='bcfcb4e1737e8140fab9c94aec6128c4a086ab5fa953e07159813abb11819d10',old_outline=[164.16,345.6],candidate_outline=[172.8,345.6],aspect=2.0,rows=rows,types=len(rows),outside=sum(not r['contained']for r in rows),overlap_types=sum(bool(r['overlaps'])for r in rows),min_neighbor_separation_um=min(r['min_bbox_separation_um']for r in rows if r['min_bbox_separation_um']is not None),added_cycles=0)
Path('/tmp/ves_width_fit.json').write_text(json.dumps(R,indent=2));print({k:v for k,v in R.items()if k!='rows'});print('bad',[(r['type'],r['contained'],r['overlaps'])for r in rows if not r['contained']or r['overlaps']][:6])
