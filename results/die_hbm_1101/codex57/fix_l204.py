import json,sys,numpy as np
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/die_plan')
import schema as S,check as C
from gen_phys import type_pins
raw=json.load(open(sys.argv[1])); p=S.Plan(raw,None); ledger=[]
for lid in ['L204','L204m']:
 xs=p.lane_crossings(lid); _,old,_=C.lane_geometry(p,lid)
 candidates=[]; owners=[]; edge_via=[]
 for ci,(part,slot,a,b) in enumerate(xs):
  ty=p.types[p.parts[part]['type']]; s=p.slot(part,slot); k=int(s['stations']);w,h=ty['outline_um']
  pins=[v for v in type_pins(p,p.parts[part]['type']) if v[0] in (slot+'_i',slot+'_o')]
  A=np.mean([[v[3],v[4]] for v in pins if v[0].endswith('_i')],axis=0);B=np.mean([[v[3],v[4]] for v in pins if v[0].endswith('_o')],axis=0)
  boxes=list(S.placed_macro_boxes(ty,halo=1.8).values())
  for j in range(k):
   f=(j+.5)/k;target=A+f*(B-A)
   grid=np.array([(x,y) for x in np.arange(8.64,w-4.32,8.64) for y in np.arange(max(4.32,np.floor((target[1]-230)/8.64)*8.64),min(h-4.32,target[1]+230),8.64) if abs(x-target[0])+abs(y-target[1])<=270])
   keep=np.ones(len(grid),dtype=bool)
   for x0,y0,x1,y1 in boxes:keep &= ~((grid[:,0]>x0)&(grid[:,0]<x1)&(grid[:,1]>y0)&(grid[:,1]<y1))
   grid=grid[keep];grid=grid[np.argsort(abs(grid-target).sum(1))[:500]]
   assert len(grid)
   candidates.append(np.array([p.to_die(part,q) for q in grid]));owners.append((part,slot,j,grid))
   edge_via.append(None if j or not ci else [p.port_point(xs[ci-1][3]),p.port_point(a)])
 costs=abs(candidates[0]-np.array(old[0])).sum(1);backs=[]
 for i in range(1,len(candidates)):
  if edge_via[i]:
   a,b=np.array(edge_via[i]);dist=abs(candidates[i-1]-a).sum(1)[None,:]+abs(b-a).sum()+abs(candidates[i]-b).sum(1)[:,None]
  else:dist=abs(candidates[i][:,None,:]-candidates[i-1][None,:,:]).sum(2)
  z=np.maximum(costs[None,:],dist)+dist*1e-5
  back=z.argmin(1);costs=z[np.arange(len(back)),back];backs.append(back)
 costs=np.maximum(costs,abs(candidates[-1]-np.array(old[-1])).sum(1)); c=costs.argmin();choice=[c]
 for b in reversed(backs):c=b[c];choice.append(c)
 choice.reverse()
 for (part,slot,j,grid),q in zip(owners,choice):p.slot(part,slot)['regs_um'][j]=list(np.round(grid[q],4))
 _,regs,_=C.lane_geometry(p,lid); hops=C.lane_pin_hops(p,lid,regs)
 print(lid,'old',max(C.lane_pin_hops(p,lid,old)),'new',hops,'max',max(hops));assert max(hops)<394.9
 ledger.append(dict(lane=lid,old_regs=old,new_regs=regs,hops_um=hops,added_cycles=0))
json.dump(raw,open(sys.argv[2],'w'),indent=0);json.dump(ledger,open(sys.argv[2]+'.ledger.json','w'),indent=2)
