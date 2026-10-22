#!/usr/bin/env python3
import json,math,time
from pathlib import Path
D=json.loads(Path('input.json').read_text());P=D['placement'];W,H=D['die_um'];G=43.2;HALO=21.6
start=time.time()
def hits(a,b):
 dx=max(0,min(a['x']+a['w']+HALO,b['x']+b['w'])-max(a['x']-HALO,b['x']))
 dy=max(0,min(a['y']+a['h']+HALO,b['y']+b['h'])-max(a['y']-HALO,b['y']))
 return dx*dy
replan={k:r for k,r in P.items() if r['m'].startswith(('hbfd_rly_','hbfd_land_','hbfd_lh_','hbfd_lh0_'))}
fixed={k:r for k,r in P.items() if k not in D['replacements'] and k not in replan}
fixed.update({'corridor:'+r['name']:r for r in D['corridors']})
result={'status':'GEOMETRY_MODEL_ONLY','input_manifest_sha256':D['manifest_sha256'],'die_um':[W,H],'body_area_before_mm2':sum(r['w']*r['h'] for r in P.values())/1e6,'body_area_after_mm2':(sum(r['w']*r['h'] for r in P.values())+sum(r['w']*r['h']-P[k]['w']*P[k]['h'] for k,r in D['replacements'].items()))/1e6,'grid_um':388.8,'clearance_um':HALO,'relay_bodies_requiring_replan':len(replan),'attempts':{},'placed':{},'explicit_open':['Relays covered by new bodies must be regenerated; none is silently dropped.','New hard parents need real feedthrough/corridor contracts, internal source clocks and full programme calendar.','This coarse bounded placement is neither a complete packing proof nor a physical signoff.']}
for name,shape in D['replacements'].items():
 old=P[name];xs=[i*388.8 for i in range(1,int((W-shape['w'])/388.8)+1)];ys=[i*388.8 for i in range(1,int((H-shape['h'])/388.8)+1)]
 xs += [math.ceil(old['x']/G)*G];ys += [math.ceil(old['y']/G)*G]
 candidates=[]
 for x in xs:
  for y in ys:
   if x+shape['w']>W or y+shape['h']>H:continue
   a={'x':x,'y':y,**shape};blockers=[]
   if any(hits(a,r)>0 for k,r in fixed.items() if k.startswith('corridor:')):continue
   for k,r in fixed.items():
    if k.startswith('corridor:'):continue
    area=hits(a,r)
    if area:blockers.append((k,area))
   score=(sum(a for _,a in blockers),len(blockers),abs(x-old['x'])+abs(y-old['y']))
   candidates.append((score,a,blockers))
 candidates.sort(key=lambda t:t[0]);top=candidates[:3]
 result['attempts'][name]={'candidates':len(candidates),'best':[{'rectangle':a,'overlap_area_um2':score[0],'blockers': [{'instance':k,'master':fixed[k].get('m'),'area_um2':area} for k,area in bs]} for score,a,bs in top]}
 if top and not top[0][2]:
  a=top[0][1];fixed[name]=a;result['placed'][name]=a
result['runtime_s']=time.time()-start
result['status']='MODEL_PLACEMENT_FOUND_RELAYS_AND_CLOCK_CALENDAR_OPEN' if len(result['placed'])==len(D['replacements']) else 'FIXED_OTHER_BODY_COMPOSITION_BLOCKED_ON_BOUNDED_GRID'
Path('composition.json').write_text(json.dumps(result,indent=1)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['attempts']}))
