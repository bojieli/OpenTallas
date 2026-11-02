import json,gzip,math,collections
from pathlib import Path
r=Path(__file__).resolve().parent;p=json.load(gzip.open(r/'FINITE_JOINT_PROBLEM.json.gz'));mov=p['movable'];fixed=p['immutable'];b={f:n['uv_bounds'][:]for f,n in mov.items()};adj=collections.defaultdict(set);W,H=p['geometry']['actual_core_box_um'][2:]
for a,c in p['edges']:adj[a].add(c);adj[c].add(a)
for f in mov:
 for v in adj[f]:
  if v not in fixed:continue
  x,y=fixed[v]['center_um'];z=b[f];b[f]=[max(z[0],x+y-399),min(z[1],x+y+399),max(z[2],x-y-399),min(z[3],x-y+399)]
q=collections.deque(mov);queued=set(mov)
while q:
 a=q.popleft();queued.discard(a)
 for c in adj[a]:
  if c not in mov:continue
  z=b[c];aa=b[a];nb=[max(z[0],aa[0]-399),min(z[1],aa[1]+399),max(z[2],aa[2]-399),min(z[3],aa[3]+399)]
  if nb!=z:
   b[c]=nb
   if c not in queued:q.append(c);queued.add(c)
bad=[]
for f,z in b.items():
 lo,hi,vl,vh=z;w=mov[f]['width_um'];rl=max(0,math.ceil(((lo-vh)/2-.135)/.27-1e-7));rh=min(math.floor((H-.27)/.27),math.floor(((hi-vl)/2-.135)/.27+1e-7));found=False
 for row in range(rl,rh+1):
  y=.135+row*.27;xl=max(w/2,lo-y,vl+y);xh=min(W-w/2,hi-y,vh+y)
  if math.ceil(xl/.054-1e-7)<=math.floor(xh/.054+1e-7):found=True;break
 if not found:bad.append(dict(ff=f,name=mov[f]['name'],uv_bounds=z,row_range=[rl,rh],immutable_neighbors=[x for x in adj[f]if x in fixed]))
s=dict(status='NATIVE_SITE_SINGLE_DOMAIN_AFTER_FIXED_CONTEXT',no_lattice_domain_count=len(bad),failures=bad,interpretation='Finite immutable greedy context only; no whole-source impossibility claim.');(r/'NATIVE_DOMAIN_DIAGNOSIS.json').write_text(json.dumps(s,indent=2)+'\n');print(json.dumps(s,indent=2))
