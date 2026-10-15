import random,json,math
# Cheap geometry search only; output remains unqualified until actualLEF pin checks.
random.seed(841)
base=[]
for lf in range(2):
 for k,w,h in [('xs',302.4,157.68),('bdc',112.32,142.56),('tct',194.4,71.28),('tcl0',86.4,120.96),('tcl1',86.4,120.96),('rowW',86.4,90.72),('rowE',43.2,90.72)]:base.append((f'{lf}_{k}',w,h))
base += [('beatWtransit',43.2,216),('beatNlanding',216,43.2),('beatSlanding',216,43.2),('beatE',43.2,216)]
def pack(order,W,H):
 free=[(0,0,W,H)];out=[]
 for n,w,h in order:
  w+=20;h+=20
  opts=[(min(fw-w,fh-h),max(fw-w,fh-h),fy,fx,j) for j,(fx,fy,fw,fh) in enumerate(free) if fw>=w and fh>=h]
  if not opts:return
  _,_,y,x,j=min(opts);new=[]
  for fx,fy,fw,fh in free:
   if x>=fx+fw or x+w<=fx or y>=fy+fh or y+h<=fy:new.append((fx,fy,fw,fh));continue
   if x>fx:new.append((fx,fy,x-fx,fh))
   if x+w<fx+fw:new.append((x+w,fy,fx+fw-x-w,fh))
   if y>fy:new.append((fx,fy,fw,y-fy))
   if y+h<fy+fh:new.append((fx,y+h,fw,fy+fh-y-h))
  free=[r for i,r in enumerate(new) if not any(i!=j and r[0]>=s[0] and r[1]>=s[1] and r[0]+r[2]<=s[0]+s[2] and r[1]+r[3]<=s[1]+s[3] for j,s in enumerate(new))]
  out.append(dict(name=n,x=x+10,y=y+10,w=w-20,h=h-20,orient='R0'))
 return out
best=None
for t in range(3000000):
 W=random.choice(range(500,951,10));H=random.choice(range(400,801,10))
 if best and W*H>=best['area']:continue
 if W*H<310000:continue
 order=sorted(base,key=lambda r:-(r[1]+20)*(r[2]+20)*random.uniform(.3,2))
 out=pack(order,W,H)
 if out:
  B={b['name']:b for b in out}
  def dst(n,m):
   a,b=B[n],B[m];return abs(a['x']+a['w']/2-b['x']-b['w']/2)+abs(a['y']+a['h']/2-b['y']-b['h']/2)
  if any(dst(f'{lf}_xs',ld)>330 or dst(f'{lf}_xs',f'{lf}_rowW')>380 or dst(f'{lf}_rowW',f'{lf}_rowE')>400 for lf,ld in [(0,'beatNlanding'),(1,'beatSlanding')]):continue
  if any(dst(f'{lf}_tct',f'{lf}_tcl{k}')>300 for lf in range(2)for k in range(2)):continue
  if any(B[f'{lf}_rowE']['x']+43.2<W-450 for lf in range(2)):continue
  if max(dst('beatWtransit',n)for n in ['beatNlanding','beatSlanding','beatE'])>400:continue
  best=dict(W=W,H=H,area=W*H,blocks=out);print(W,H,W*H,flush=True);json.dump(best,open('/tmp/split_connected_all.json','w'),indent=2)
