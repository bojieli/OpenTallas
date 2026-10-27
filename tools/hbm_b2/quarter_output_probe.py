import argparse,json,numpy as np
from collections import deque
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path,required=True);D=ap.parse_args().data; L=json.load(open(D/'c11_native/layout.json'))
# Exact existing b_w/e_bus stage identities; no added storage. Each slot is independently wired.
W,H=218.592,187.488
obs=L['cores']+L['srams']+L['tails']
def free(x,y):
 return not any(z['origin_um'][0]-.27<x<z['origin_um'][0]+z['outline_um'][0]+.27 and z['origin_um'][1]-.27<y<z['origin_um'][1]+z['outline_um'][1]+.27 for z in obs)
xs=list(np.arange(12,1808,24))+[8.64+c*449.28+221.616 for c in range(4)]+[1812.096]
ys=list(np.arange(12,2347,24))
pts=np.array([(x,y)for x in xs for y in ys if free(x,y)])

h1={p['name']:p for p in json.load(open(D/'pins_h1.json'))}
adj=[np.flatnonzero(np.abs(pts-p).sum(axis=1)<=405).tolist()for p in pts]
res=[]
for e in range(2):
 tail={p['name']:p for p in json.load(open(D/f'pins_tail{e}.json'))}
 # Keep native reservation orientation R0 initially; report failures and compare MX.
 for ori in (['MX']if e==0 else['R0']):
  for c in range(4):
   for k in range(4):
    for b in range(33):
     n='cf_out'if b==32 else f'cs_out[{b}]'; pp=h1[n]
     src=np.array([8.64+c*449.28+224.64+pp['x'],8.64+e*1391.04+[0,267.84,483.84,751.68][k]+(H-pp['y']if k%2 else pp['y'])])
     tn=f'ge_{e}_u_t_i_fault[{k*4+c}]'if b==32 else f'ge_{e}_u_t_i_sum[{(k*4+c)*32+b}]';tp=tail[tn]
     dst=np.array([1581.12+tp['x'],8.64+976.32+e*216+(H-tp['y']if ori=='MX'else tp['y'])])
     maxh=2*(4-c)+1
     starts=np.flatnonzero(np.abs(pts-src).sum(axis=1)<=405)
     targets=np.flatnonzero(np.abs(pts-dst).sum(axis=1)<=405)
     dist=[999]*len(pts);parent={};q=deque()
     for j in targets.tolist():dist[j]=1;q.append(j)
     startset=set(starts.tolist());best=999
     while q:
      j=q.popleft()
      if j in startset:best=dist[j]+1;break
      if dist[j]>=maxh-1:continue
      for z in adj[j]:
       if dist[z]==999:dist[z]=dist[j]+1;parent[z]=j;q.append(z)
     path=[]
     if best<=maxh:
      node=j
      while True:
       path.append(pts[node].tolist())
       if node not in parent:break
       node=parent[node]
      path=[path[0]]*(maxh-1-len(path))+path
     stage_names=[f"gc{cc}.{stage}"for cc in range(c,4)for stage in ["leaf.b_w","leaf.e_bus"]]
     res.append(dict(waypoints=[dict(identity=stage_names[ii],point_um=pp)for ii,pp in enumerate(path)],source_um=src.tolist(),target_um=dst.tolist(),e=e,c=c,k=k,bit=b,tail_orient=ori,allowed_native_hops=maxh,model_min_hops=best,pass_=best<=maxh))
summary={'free_anchor_candidates':len(pts),'extra_right_corridor_um':8.64,'qualification':'MODEL ONLY; discrete point reach, not standard-cell packing; native b_w/e_bus identities only','paths':res,'groups':[],'failures':[r for r in res if not r['pass_']]}
for e in range(2):
 for o in (['MX']if e==0 else['R0']):
  rr=[r for r in res if r['e']==e and r['tail_orient']==o];summary['groups'].append(dict(engine=e,orient=o,fail=sum(not r['pass_']for r in rr),count=len(rr),worst_excess=max(r['model_min_hops']-r['allowed_native_hops']for r in rr)))
json.dump(summary,open(D/'output_probe.json','w'),indent=2);print(summary['groups'])
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
fig,ax=plt.subplots(figsize=(10,13))
for z in obs:
 x,y=z['origin_um'];w,h=z['outline_um'];ax.add_patch(Rectangle((x,y),w,h,fc='#ddd',ec='#777',lw=.3))
for r in res:
 if r['c']==3 and r['bit']in[0,31,32]:
  p=[r['source_um']]+[v['point_um']for v in r['waypoints']]+[r['target_um']];ax.plot([v[0]for v in p],[v[1]for v in p],lw=.8,alpha=.7)
ax.set_xlim(0,1816.992);ax.set_ylim(0,2347.488);ax.set_aspect('equal');ax.set_title('Native c3 b_w/e_bus output paths; tail0 MX, tail1 R0\n1056 sum/fault paths fit native slots; point model only')
fig.savefig(D/'output_paths.png',dpi=140,bbox_inches='tight')
