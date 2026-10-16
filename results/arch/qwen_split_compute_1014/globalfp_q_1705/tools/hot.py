# Hot-cut census of a route.out: edges over the 0.60 gate, grouped into windows, with the buses that load them.
import os;FULL=os.environ.get('FULL')
import json,sys,collections
from pathlib import Path
rd=Path(sys.argv[1]);out=Path(sys.argv[2]) if len(sys.argv)>2 else rd/'route.out'
md=json.load(open(rd/'route-metadata.json'));em=md['edge_metadata'];f=open(out);f.readline()
K=len(md['nets']);netedges=[]
for k in range(K):z=list(map(int,f.readline().split()));netedges.append(z[2:])
assert f.readline().strip()=='USES';use={}
for e in range(len(em)):z=list(map(int,f.readline().split()));use[e]=z[1]
hot={e:use[e]/em[e][6] for e in use if em[e][6]>0 and use[e]/em[e][6]>0.60}
print('edges over .60:',len(hot),' worst',round(max(hot.values()) if hot else 0,3))
# window by 1 mm
win=collections.defaultdict(list)
for e,r in hot.items():
 d,ix,iy,cut,lo,hi,cap,occ=em[e];x=cut if d=='H' else (lo+hi)/2;y=(lo+hi)/2 if d=='H' else cut
 win[(d,int(x//1000),int(y//1000))].append((r,e))
bus_by_edge=collections.defaultdict(collections.Counter)
hotset=set(hot)
for k,es in enumerate(netedges):
 b=md['buses'][md['nets'][k]['rid']]['bus']
 for e in es:
  if e in hotset:bus_by_edge[e][b]+=md['nets'][k]['bits']
rows=sorted(win.items(),key=lambda kv:-max(r for r,_ in kv[1]))
for (d,x,y),L in rows[:int(sys.argv[3]) if len(sys.argv)>3 else 15]:
 worst=max(L);c=collections.Counter()
 for _,e in L:c.update(bus_by_edge[e])
 fam=collections.Counter()
 for b,n in c.items():fam[b if FULL else (b.rstrip('0123456789_').split('_')[0] if not b.startswith('ng_') else '_'.join(b.split('_')[:3]))]+=n
 print(f'{d} window x~{x}mm y~{y}mm edges {len(L)} worst {worst[0]:.3f} cap {em[worst[1]][6]:.0f} occ {em[worst[1]][7]:.2f} top', fam.most_common(5))
