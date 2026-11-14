from pathlib import Path
import random,json,math
W,H=1442.88,2747.52
G,E=43.2,34.56
spec=[('head',32,157.68,259.2),('sx',8,138.24,164.16),('sml',8,120.96,259.2),('smd',4,77.76,259.2),('smc',1,120.96,259.2),('smr',1,120.96,259.2),('h4',8,103.68,259.2),('trx',4,120.96,259.2)]
boxes=[(f'{n}{i}',math.ceil((w+G)/8.64-1e-6)*8.64,math.ceil((h+G)/8.64-1e-6)*8.64,w,h) for n,c,w,h in spec for i in range(c)]
def pack(B,hh):
 free=[(E,E,W-2*E+G,hh-2*E-328.32)]
 out=[]
 for name,w,h,ww,hh0 in B:
  cand=[(min(a-w,b-h),max(a-w,b-h),y,x,j) for j,(x,y,a,b) in enumerate(free) if a>=w-1e-6 and b>=h-1e-6]
  if not cand:return out
  _,_,y,x,j=min(cand);out.append(dict(name=name,x=x,y=y,w=ww,h=hh0))
  new=[]
  for fx,fy,fw,fh in free:
   if x>=fx+fw-1e-6 or x+w<=fx+1e-6 or y>=fy+fh-1e-6 or y+h<=fy+1e-6:new.append((fx,fy,fw,fh));continue
   if x>fx:new.append((fx,fy,x-fx,fh))
   if x+w<fx+fw:new.append((x+w,fy,fx+fw-x-w,fh))
   if y>fy:new.append((fx,fy,fw,y-fy))
   if y+h<fy+fh:new.append((fx,y+h,fw,fy+fh-y-h))
  free=[r for k,r in enumerate(new) if not any(k!=l and r[0]>=q[0]-1e-6 and r[1]>=q[1]-1e-6 and r[0]+r[2]<=q[0]+q[2]+1e-6 and r[1]+r[3]<=q[1]+q[3]+1e-6 and (r!=q or k>l) for l,q in enumerate(new))]
 return out
best=[]
for grow in [0,103.68,112.32]:
 best=[]
 for seed in range(10000):
  random.seed(seed);B=sorted(boxes,key=lambda b:-(b[1]*b[2])*(1+random.uniform(-.8,.8)))
  out=pack(B,H+grow)
  if len(out)>len(best):best=out
  if len(out)==len(boxes):break
 r=dict(status='PACKING_ONLY_NO_SOURCE_CUT_NO_PIN_REVIEW',growth_um=grow,placed=len(best),total=len(boxes),outline_um=[W,H+grow],Satt_assumed_height_um=328.32,street_um=G,edge_um=E,placements=best)
 Path(f'/srv/opentallas-scratch2/claude/hard-s81-svc-1/packing_{grow}.json').write_text(json.dumps(r,indent=1))
 print(grow,len(best),len(boxes),seed)
