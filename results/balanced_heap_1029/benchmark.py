import sys,time,pathlib,json,hashlib
R=pathlib.Path('/srv/opentallas-scratch2/claude/codex-icg-tree-1028');sys.path.insert(0,str(R/'perf_src'))
import core_infra_htree as H
from test_balanced_heap import legacy_balanced
points=[]
for l in (R/'w/ot_v41_bf_col/geo_entry.txt').open():
 f=l.split()
 if f[:1]==['SINK']:points.append((float(f[1]),float(f[2]),f[4],f[5]))
 if len(points)==8192:break
ordered=sorted(points,key=lambda p:p[0]);k=8
centres=[ordered[int((i+.5)*len(ordered)/k)][:2] for i in range(k)]
dist=lambda p,c:abs(p[0]-c[0])+abs(p[1]-c[1])
t=time.perf_counter();old=legacy_balanced(points,centres,dist,iters=300);old_s=time.perf_counter()-t
print('legacy seconds',old_s,flush=True)
t=time.perf_counter();new=H.balanced(points,centres,dist,iters=300);new_s=time.perf_counter()-t
assert new==old
rec=dict(points=len(points),groups=k,iterations=300,legacy_seconds=old_s,new_seconds=new_s,speedup=old_s/new_s,exact_assignment=True,sha256=hashlib.sha256(repr(new).encode()).hexdigest())
(R/'balanced_benchmark.json').write_text(json.dumps(rec,indent=1));print(json.dumps(rec),flush=True)
