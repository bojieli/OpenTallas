# Longest run along each routed root->sink path whose grid-cell centres lie inside hard bodies (no relay site),
# per bus; reports buses whose run exceeds 500 um (a relay every <=500 um cannot be placed on that route).
import json,sys,collections,numpy as np
from pathlib import Path
rd=Path(sys.argv[1]);outp=sys.argv[2];homes=json.load(open(sys.argv[3]))['homes']
md=json.load(open(rd/'route-metadata.json'));ny=md['ny'];B=md['grid_um'];gx=md['grid_centers_x'];gy=md['grid_centers_y'];nx=md['nx']
blk=np.zeros((nx,ny),bool)
for i in homes.values():
 x0=int(np.searchsorted(gx,i['x']));x1=int(np.searchsorted(gx,i['x']+i['w']));y0=int(np.searchsorted(gy,i['y']));y1=int(np.searchsorted(gy,i['y']+i['h']))
 blk[x0:x1,y0:y1]=True
inp=open(rd/'route.in');h=inp.readline().split();E=int(h[3]);edges=[tuple(map(int,inp.readline().split()[:2])) for _ in range(E)]
f=open(outp);f.readline();worst=collections.defaultdict(float);fam=collections.Counter()
for k,net in enumerate(md['nets']):
 z=list(map(int,f.readline().split()));adj=collections.defaultdict(list)
 for e in z[2:]:u,v=edges[e];adj[u].append(v);adj[v].append(u)
 r=net['terms'][0];run={r:0 if not blk[r//ny,r%ny] else 1};best=0;q=[r];seen={r}
 for u in q:
  for v in adj[u]:
   if v in seen:continue
   seen.add(v);run[v]=run[u]+1 if blk[v//ny,v%ny] else 0;best=max(best,run[v]);q.append(v)
 b=md['buses'][net['rid']]['bus'];worst[b]=max(worst[b],best*B)
bad={b:L for b,L in worst.items() if L>500}
for b in bad:fam[b.rstrip('0123456789_').split('_')[0]]+=1
print(json.dumps({'buses':len(worst),'buses_blocked_run_gt_500um':len(bad),'families':fam.most_common(12),'worst':sorted(bad.items(),key=lambda x:-x[1])[:12]}))
