import json,math,collections
from pathlib import Path
P=Path(__file__).resolve().parent
source=(P/'kit/joint_model.py').read_text();ns={'__file__':str(P/'kit/joint_model.py')}
exec(compile(source.split('plan={};grid=')[0].replace("O=P/'out'","O=P/'definition_demands'"),str(P/'kit/joint_model.py'),'exec'),ns)
items=ns['items'];areas=ns['areas'];alloc=ns['allocation']
# Deterministic actual interval packing, no placement engine. Native functional
# multirow rectangles first; every real one-row atom follows largest-first.
def pack(its,W,H,emit=False):
 rows=[[] for _ in range(H)];placements=[]
 for it in sorted(its,key=lambda x:(-x['h'],-x['w'],x['id'])):
  w=it['w'];h=it['h'];best=None
  for y in range(H-h+1):
   starts={8}
   for rr in range(y,y+h):
    starts.update(b for a,b in rows[rr])
   for x in sorted(starts):
    if x+w>W-8:continue
    if any(any(x<b and x+w>a for a,b in rows[rr]) for rr in range(y,y+h)):continue
    score=(x+w,y,x)
    if best is None or score<best:best=score
  if best is None:return None
  end,y,x=best
  for rr in range(y,y+h):rows[rr].append((x,x+w))
  placements.append({'id':it['id'],'xsite':x,'row':y,'width_sites':w,'height_rows':h})
 return placements
result={};demand={}
for H in [32,36]:
 result[H]={}
 for g in sorted(areas):
  its=[i for i in items if i['cohort']==g]
  minimum=max(max(i['w'] for i in its)+16,math.ceil(sum(i['w']*i['h'] for i in its)/H)+16,math.ceil(areas[g]/(.6*.054*.27*H)))
  maximum=math.floor(areas[g]/(.4*.054*.27*H))
  # Binary search finite constructive demand; failed packing need not be monotone
  # in general. Retain last known feasible candidate; verify it before use.
  lo=minimum;hi=max(maximum,minimum)
  feasible=pack(its,hi,H)
  if feasible is None:result[H][g]={'status':'NO_FEASIBLE_NATIVE_DENSITY_INTERVAL','min_sites':minimum,'max_sites':maximum};continue
  while lo<hi:
   mid=(lo+hi)//2
   if pack(its,mid,H) is None:lo=mid+1
   else:hi=mid
  placements=pack(its,hi,H);assert placements is not None
  result[H][g]={'status':'FINITE_CONTIGUOUS_PACK','width_sites':hi,'rows':H,'native_fill':areas[g]/(hi*H*.054*.27),'reserved_atom_sites':sum(i['w']*i['h'] for i in its),'routing_side_reserve_sites':16,'placements':placements}
print(json.dumps({H:{g:{k:v for k,v in z.items() if k!='placements'} for g,z in gs.items()} for H,gs in result.items()}))
(P/'DEMANDS.json').write_text(json.dumps(result))
(P/'ACTUAL_ITEMS.json').write_text(json.dumps(items))
(P/'DEMAND_SOURCE_GROUPS.json').write_text(json.dumps({'allocation':alloc,'areas':areas,'co':ns['co'],'byname':ns['byname']}))
