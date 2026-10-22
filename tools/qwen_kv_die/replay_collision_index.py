"""Replay captured relay candidates against the original collision scan and spatial lookup."""
import gzip,json,sys,time
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parent))
from kv_pin_repair import CollisionIndex
p=Path(sys.argv[1]);r=json.loads(gzip.decompress(p.read_bytes()))
added={x['relay']:x['bus'] for x in r['pin_repair']['added']}
index=CollisionIndex([]);global_rows=[];staged=[];last=None
count=positive=accepted_collision=0;linear_time=index_time=0.0
for row in r['insts']:
 it=SimpleNamespace(**row);bus=added.get(it.name)
 if bus is not None:
  if bus!=last:
   for q in staged:index.add(q)
   global_rows.extend(staged);staged=[];last=bus
  w,h=it.w+.024,it.h+.024
  for dx in (-21.6,0,21.6):
   for dy in (-21.6,0,21.6):
    x,y=it.x+dx,it.y+dy
    def overlap(q):
     return min(x+w+4.32,q.x+q.w)-max(x-4.32,q.x)>.001 and min(y+h+4.32,q.y+q.h)-max(y-4.32,q.y)>.001
    t=time.perf_counter();old=any(overlap(q) for q in global_rows+staged);linear_time+=time.perf_counter()-t
    t=time.perf_counter();cand=index.candidates(x-4.32,y-4.32,x+w+4.32,y+h+4.32);new=any(overlap(q) for q in cand+staged);index_time+=time.perf_counter()-t
    if old!=new:raise AssertionError((it.name,dx,dy,old,new))
    count+=1;positive+=old;accepted_collision+=old and dx==0 and dy==0
  staged.append(it)
 else:
  if staged:
   for q in staged:index.add(q)
   global_rows.extend(staged);staged=[];last=None
  index.add(it);global_rows.append(it)
print(json.dumps(dict(source=r['source'],pickle_sha256=r['pickle_sha256'],obstacles=len(r['insts']),captured_accepted_candidates=len(added),queries=count,overlap_queries=positive,accepted_candidate_collisions=accepted_collision,mismatches=0,linear_seconds=linear_time,index_seconds=index_time,speedup=linear_time/index_time,scope='Actual captured accepted relay candidates plus eight lattice neighbours, exact original float predicate and actual staged/committed obstacle order'),indent=2))
