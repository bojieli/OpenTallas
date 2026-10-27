import json,numpy as np
from pathlib import Path
p=Path(__file__).parent;D=json.loads((p/'hub_boxes.json').read_text());O={}
w,h=241.92,293.76;m=8.64
for tn,t in D.items():
 W,H=t['outline_um'];B=[]
 for x in t['hard_cores']+t['contents']:
  if 'keybuf' in x['inst'] or 'origin_um' not in x or 'outline_um' not in x:continue
  xx,yy=x['origin_um'];ww,hh=x['outline_um'];B.append((xx,yy,xx+ww,yy+hh))
 allslots=[]
 for seg in range(2):
  lo,hi=(m,3957.12-m)if seg==0 else(3957.12+m,W-m)
  X,Y=np.meshgrid(np.arange(lo,hi-w,m),np.arange(m,H-h-m,m));X=X.ravel();Y=Y.ravel();ok=np.ones(len(X),bool)
  for x0,y0,x1,y1 in B:ok&=~((X+w+m>x0)&(X-m<x1)&(Y+h+m>y0)&(Y-m<y1))
  idx=next(x for x in t['hard_cores']if x['inst']==f'u_hb_idx__q_Q__q{seg}')
  ix,iy=idx['origin_um'];iw,ih=idx['outline_um'];cost=np.abs(X+w/2-ix-iw/2)+np.abs(Y+h/2-iy-ih/2)
  slots=[]
  for k in range(8):
   if not ok.any():break
   j=int(np.argmin(np.where(ok,cost,np.inf)));xx,yy=float(X[j]),float(Y[j]);slots.append([round(xx,2),round(yy,2)]);
   ok&=~((X+w+m>xx)&(X-m<xx+w)&(Y+h+m>yy)&(Y-m<yy+h))
  allslots.append({'segment':seg,'placed':len(slots),'origins_um':slots,'target_centre_um':[ix+iw/2,iy+ih/2]})
 O[tn]=allslots
(p/'pack_lots.json').write_text(json.dumps(O,indent=2)+'\n');print(json.dumps(O))
