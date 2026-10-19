from pathlib import Path
import json,math,collections
P=Path('.').resolve();g=json.loads((P/'reset_root_place.json').read_text());pos=g['positions'];original=g['parents'];code=(P/'reset_access_bridges.py').read_text();a=code.index('def m6_near');b=code.index('# Try legal R0 bridge bodies',a);exec(code[a:b]);bucket=collections.defaultdict(list);B=440
for n,(x,y,*_)in pos.items():bucket[int(x//B),int(y//B)].append(n)
root=next(n for n,p in original.items()if p is None)
def neighbors(n):
 x,y,*_=pos[n];bx,by=int(x//B),int(y//B);out=[]
 for dx in(-1,0,1):
  for dy in(-1,0,1):
   for m in bucket[bx+dx,by+dy]:
    if m!=n:
     d=dist(n,m)
     if d<=405.000001:out.append((d,m))
 return sorted(out)
results=[]
for limit in[8,14,16]:
 par={root:None};depth={root:0};q=collections.deque([root]);degree=collections.Counter()
 while q:
  n=q.popleft()
  for d,m in neighbors(n):
   if m in par:continue
   if degree[n]>=limit:break
   par[m]=n;depth[m]=depth[n]+1;degree[n]+=1;q.append(m)
 result={'child_limit':limit,'logical_child_input_load_limit':2*limit,'nodes':len(pos),'connected':len(par),'unreachable':[n for n in pos if n not in par],'max_child_degree':max(degree.values()),'max_depth_after_root0':max(depth.values()),'max_both_input_escape_um':max(dist(p,n)for n,p in par.items()if p),'scope':'DEGREE_LIMITED_ACTUAL_TRACK_ESCAPE_GRAPH_ONLY_PRODUCTION_SINKS_ICG_NATIVE_CLOCK_RC_CALENDAR_STILL_OWED'};results.append(result)
 (P/f'reset_degree{limit}_graph.json').write_text(json.dumps({'summary':result,'parents':par,'positions':pos},indent=1)+'\n')
print(json.dumps(results,indent=1));(P/'reset_degree_graph_summary.json').write_text(json.dumps(results,indent=1)+'\n')
