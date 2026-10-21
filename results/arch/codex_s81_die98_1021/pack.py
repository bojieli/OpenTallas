import json,random,sys
from pathlib import Path
root=Path(sys.argv[1]);d=json.loads((root/'input.json').read_text());W,H=d['die'];gap=d['clearance']
def hit(a,b):return a[0]<b[0]+b[2]-1e-6 and b[0]<a[0]+a[2]-1e-6 and a[1]<b[1]+b[3]-1e-6 and b[1]<a[1]+a[3]-1e-6
def cut(free,r):
 out=[]
 for f in free:
  if not hit(f,r):out.append(f);continue
  x,y,w,h=f; a,b,c,e=r
  if a>x:out.append((x,y,a-x,h))
  if a+c<x+w:out.append((a+c,y,x+w-a-c,h))
  if b>y:out.append((x,y,w,b-y))
  if b+e<y+h:out.append((x,b+e,w,y+h-b-e))
 out=[f for f in out if f[2]>1e-4 and f[3]>1e-4]
 return [f for i,f in enumerate(out) if not any(i!=j and g[0]<=f[0]+1e-6 and g[1]<=f[1]+1e-6 and g[0]+g[2]>=f[0]+f[2]-1e-6 and g[1]+g[3]>=f[1]+f[3]-1e-6 and (g!=f or j<i) for j,g in enumerate(out))]
base=[(0,0,W,H)]
for b in d['fixed']:
 r=(b['x']-gap/2,b['y']-gap/2,b['w']+gap,b['h']+gap);base=cut(base,r)
results=[];best=None
for strategy in range(12):
 rng=random.Random(strategy)
 rr=list(d['rectangles'])
 if strategy%4==0:rr.sort(key=lambda r:-(r['w']+gap)*(r['h']+gap))
 elif strategy%4==1:rr.sort(key=lambda r:-max(r['w'],r['h']))
 elif strategy%4==2:rr.sort(key=lambda r:-(r['w']+gap)*(r['h']+gap)*(0.8+0.4*rng.random()))
 else:rr.sort(key=lambda r:-(r['h']+gap))
 free=list(base);placed=[];unplaced=[]
 for r in rr:
  w,h=r['w']+gap,r['h']+gap
  choices=[]
  for f in free:
   x,y,fw,fh=f
   if w<=fw+1e-6 and h<=fh+1e-6:
    score=(min(fw-w,fh-h),max(fw-w,fh-h),y,x) if strategy<8 else (y+h,x,min(fw-w,fh-h))
    choices.append((score,x,y))
  if not choices:unplaced.append(r);continue
  _,x,y=min(choices);placed.append(dict(r,x=x+gap/2,y=y+gap/2));free=cut(free,(x,y,w,h))
 trial=dict(strategy=strategy,placed=len(placed),unplaced=len(unplaced),unplaced_names=[r['name'] for r in unplaced],unplaced_mm2=sum(r['w']*r['h'] for r in unplaced)/1e6)
 results.append(trial);print(json.dumps(trial),flush=True)
 if best is None or trial['unplaced_mm2']<best['trial']['unplaced_mm2']:best=dict(trial=trial,blocks=d['fixed']+placed,unplaced=unplaced)
 if not unplaced:break
out=dict(scope=d['scope'],die=d['die'],clearance=gap,body_mm2=sum(r['w']*r['h'] for r in d['rectangles']+d['fixed'])/1e6,attempts=results,best=best,obligations=d['obligations'],verdict='MODEL_RECTANGLES_PACKED_SOURCE_AND_HOPS_OWED' if not best['unplaced'] else 'HEURISTIC_NO_FIT_NOT_INFEASIBILITY_PROOF')
(root/'packing.json').write_text(json.dumps(out,indent=2));print(out['verdict'],out['body_mm2'])
