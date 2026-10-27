"""Native-4-quarter physical lot probe; does not edit a plan or authorize route."""
import json,sys,pathlib,numpy as np,math,re
pd,out=sys.argv[1:];pd=pathlib.Path(pd);raw=json.loads((pd/'die_plan.json').read_text());report={};G=4.32;halo=4.32
class Floor:
 def __init__(self,t,remove_keybuf=False):
  self.t=t;self.W,self.H=t['outline_um'];self.nx,self.ny=int(self.W/G),int(self.H/G);self.a=np.zeros((self.ny,self.nx),dtype=np.uint8)
  for h in t.get('hard_cores',[]):
   if not remove_keybuf or 'keybuf' not in h['module']:self.block(self.rect(h),halo)
  for c in t.get('contents',[]):
   if 'origin_um' in c and 'outline_um' in c and (not remove_keybuf or 'keybuf' not in c['inst']):self.block(self.rect(c),halo)
  for box in [[0,0,self.W,G],[0,self.H-G,self.W,self.H],[0,0,G,self.H],[self.W-G,0,self.W,self.H]]:self.block(box)
 @staticmethod
 def rect(c):x,y=c['origin_um'];w,h=c['outline_um'];return [x,y,x+w,y+h]
 def block(self,r,ext=0):
  x0,y0,x1,y1=r;x0=max(0,int(math.floor((x0-ext)/G)));x1=min(self.nx,int(math.ceil((x1+ext)/G)));y0=max(0,int(math.floor((y0-ext)/G)));y1=min(self.ny,int(math.ceil((y1+ext)/G)));self.a[y0:y1,x0:x1]=1
 def place(self,wh,target):
  cw,ch=wh;bw,bh=math.ceil((cw+2*halo)/G),math.ceil((ch+2*halo)/G)
  cs=np.pad(self.a.cumsum(0,dtype=np.int64).cumsum(1),((1,0),(1,0)));s=cs[bh:,bw:]-cs[:-bh,bw:]-cs[bh:,:-bw]+cs[:-bh,:-bw];ys,xs=np.where(s==0)
  if not len(xs):return None
  score=abs(xs*G+halo+cw/2-target[0])+abs(ys*G+halo+ch/2-target[1]);i=int(np.argmin(score));x,y=xs[i]*G+halo,ys[i]*G+halo
  self.block([x-halo,y-halo,x+cw+halo,y+ch+halo]);return dict(origin_um=[round(float(x),3),round(float(y),3)],outline_um=list(wh),target_distance_um=round(float(score[i]),3))
for tn,logical in [('q_hub_nw','SW'),('q_hub_ne','SE')]:
 t=raw['partition_types'][tn];f=Floor(t,True);svg=sorted([h for h in t['hard_cores'] if h['inst'].startswith('u_svg_')],key=lambda x:x['inst']);placed=[];fail=[];pc_centers={}
 # True four-line quarter buffers: each PC line first, then its 16 half-columns.
 for pc in range(4):
  h=svg[pc];target=[h['origin_um'][0]+h['outline_um'][0]/2,h['origin_um'][1]+h['outline_um'][1]/2]
  item=f.place([241.92,293.76],target)
  if not item:fail.append(['keybuf',pc]);continue
  item.update(kind='keybuf',pc=pc,logical_quarter=logical);placed.append(item);pc_centers[pc]=[item['origin_um'][0]+120.96,item['origin_um'][1]+146.88]
 for pc in range(4):
  if pc not in pc_centers:continue
  for c in range(4):
   for k in [2*(pc%2),2*(pc%2)+1]:
    for h in range(2):
     item=f.place([218.592,187.488],pc_centers[pc])
     key=f'r{pc//2}c{c}_k{k}h{h}'
     if not item:fail.append(['hcol',pc,key]);continue
     item.update(kind='hcol',pc=pc,member=key,logical_quarter=logical);placed.append(item)
 for e in range(2):
  centers=[pc_centers[x] for x in [2*e,2*e+1] if x in pc_centers];target=[sum(p[i] for p in centers)/len(centers) for i in range(2)] if centers else [f.W/2,f.H/2]
  item=f.place([218.592,187.488],target)
  if not item:fail.append(['tail',e]);continue
  item.update(kind='tail',engine=e,logical_quarter=logical);placed.append(item)
 report[tn]=dict(scope='model-only4keybuf+64hcol+2tail restore, old internal/FT stations must be re-sited',placed=len(placed),requested=70,failed=fail,placements=placed)
 print(tn,len(placed),'of70',len(fail),'fail',flush=True)
# Retained quarter key lines require lots near existing scorers, not query proxies in the hub.
report['retained_keybuf_lots']={}
for tn,pc in [('q_b100',0),('q_b101',1),('q_b102',2),('q_b103',3)]:
 t=raw['partition_types'][tn];f=Floor(t);item=f.place([241.92,293.76],[t['outline_um'][0]/2,t['outline_um'][1]-146.88]);report['retained_keybuf_lots'][tn]=dict(pc=pc,placement=item,scope='sharedNW/NEtype origin, stations must be re-sited')
 print(tn,'keybuf','PASS' if item else 'FAIL',flush=True)
pathlib.Path(out).write_text(json.dumps(report,indent=1)+'\n')
