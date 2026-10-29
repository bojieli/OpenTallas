"""DIE-KV-31: residual failed rails vs die M8 clock NDR reservations (die_trial.reserve_rects, BLOCK M8 0.40-um tall)."""
import json,sys,collections
from shapely.geometry import box
from shapely.strtree import STRtree
ov=json.load(open(sys.argv[1]));pl=json.load(open(sys.argv[2]+'/access_plan.json'))
m8=[o[2:] for o in ov['obstructions'] if o[0]=='BLOCK' and o[1]=='M8' and o[5]-o[3]==400]
t=STRtree([box(*r) for r in m8]);c=collections.Counter()
for q in pl['failed']:
  x0,y0,x1,y1=q['rail'];cy=(y0+y1)//2
  for R in (1400,5400,10800):
    if len(t.query(box(x0,cy-R,x1,cy+R))):c[f'clock_M8_reserve_within_{R/1000}um']+=1;break
  else:c['no_clock_reserve_within_10.8um']+=1
print(json.dumps(dict(m8_clock_reserve_rects=len(m8),failed=len(pl['failed']),by=c)))
