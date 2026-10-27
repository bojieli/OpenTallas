import json,numpy as np,itertools,collections,math
from scipy.optimize import linprog
P=json.load(open('/tmp/pv_current.json'));moves=[];fails=[]
def box(h):
 x,y=h['origin_um'];dx,dy=h.get('track_offset_um',[0,0]);w,hh=h['outline_um'];return min(x,x+dx),min(y,y+dy),max(x+w,x+dx+w),max(y+hh,y+dy+hh)
def hit(a,b):return min(a[2],b[2])-max(a[0],b[0])>1e-7 and min(a[3],b[3])-max(a[1],b[1])>1e-7
for tn,t in P['partition_types'].items():
 if not any(h['module']=='ot_qwen_tp8_pv_join_t' for h in t.get('hard_cores',[])):continue
 boxes=[box(h) for h in t['hard_cores']]
 for slot in t.get('ft_slots',[]):
  gs=slot.get('bit_sites_um',[]);n=len(gs);wh=slot.get('bit_site_cell_um',[1.404,.27]);bbs=[[min(q[0] for q in g),min(q[1] for q in g),max(q[0]+wh[0] for q in g),max(q[1]+wh[1] for q in g)] for g in gs]
  collisions=[(j,b) for j,a in enumerate(bbs) for b in boxes if hit(a,b)]
  if not collisions:continue
  best=None
  for choices in itertools.product(range(4),repeat=len(collisions)):
   A=[];B=[];bounds=[(-80,80)]*(2*n)+[(0,None)]*(2*n);c=np.r_[np.zeros(2*n),np.ones(2*n)]
   def add(items,b):
    a=np.zeros(4*n)
    for k,v in items:a[k]=v
    A.append(a);B.append(b)
   for k in range(2*n):add([(k,1),(2*n+k,-1)],0);add([(k,-1),(2*n+k,-1)],0)
   choice=dict((j,side) for (j,_),side in zip(collisions,choices))
   for j,a in enumerate(bbs):
    for b in boxes:
     opts=[(j*2,1,b[0]-a[2]-.27),(j*2,-1,a[0]-b[2]-.27),(j*2+1,1,b[1]-a[3]-.54),(j*2+1,-1,a[1]-b[3]-.54)]
     if hit(a,b):o=opts[choice[j]]
     else:o=max((o for o in opts if o[2]>=-1e-7),key=lambda o:o[2],default=None)
     if o:add([(o[0],o[1])],o[2])
   for j in range(n-1):
    for a,b in zip(gs[j],gs[j+1]):
     for sx,sy in itertools.product((-1,1),repeat=2):add([(2*j,sx),(2*j+1,sy),(2*j+2,-sx),(2*j+3,-sy)],404-sx*(a[0]-b[0])-sy*(a[1]-b[1]))
   # Keep boundary stations unchanged, preserving their face-to-station legs.
   for k in (0,1,2*n-2,2*n-1):bounds[k]=(0,0)
   r=linprog(c,A_ub=A,b_ub=B,bounds=bounds,method='highs')
   if r.success and (best is None or r.fun<best.fun):best=r
  if best is None:fails.append((tn,slot['name'],len(collisions)));continue
  new=[]
  for j,g in enumerate(gs):
   dx=round(best.x[2*j]/.054)*.054;dy=round(best.x[2*j+1]/.27)*.27;ng=[[round(q[0]+dx,6),round(q[1]+dy,6)] for q in g];new.append(ng)
   if abs(dx)+abs(dy)>1e-6:moves.append(dict(type=tn,slot=slot['name'],stage=j+1,old=g,new=ng,delta_um=[dx,dy],cycles_added=0))
  slot['bit_sites_um']=new
print('MOVED',len(moves),'FAIL',fails)
json.dump(P,open('/tmp/pv_solved.json','w'),indent=1);json.dump(moves,open('/tmp/pv_solved_delta.json','w'),indent=1);json.dump(fails,open('/tmp/pv_solved_pending.json','w'),indent=1)
