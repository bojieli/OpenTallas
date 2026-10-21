"""Construct an independent body packing. Does not preserve old physical paths/dates."""
import json,copy,random,time,hashlib
from pathlib import Path
root=Path(__file__).resolve().parent;p=json.loads((root/'input.json').read_text());G=86400;S=100000;R=32900000;T=25900000
# integers are nm, all body dimensions unchanged except exact H10 candidate.
def U(x):return round(x*1000)
def intersects(a,b):return a[0]<b[0]+b[2]and b[0]<a[0]+a[2]and a[1]<b[1]+b[3]and b[1]<a[1]+a[3]
def contains(a,b):return a[0]<=b[0]and a[1]<=b[1]and a[0]+a[2]>=b[0]+b[2]and a[1]+a[3]>=b[1]+b[3]
def cut(free,b):
 out=[]
 for a in free:
  if not intersects(a,b):out.append(a);continue
  x,y,w,h=a;X,Y,W,H=b
  if X>x:out.append((x,y,X-x,h))
  if X+W<x+w:out.append((X+W,y,x+w-X-W,h))
  if Y>y:out.append((x,y,w,Y-y))
  if Y+H<y+h:out.append((x,Y+H,w,y+h-Y-H))
 out=list(dict.fromkeys(out));return[a for i,a in enumerate(out)if a[2]>0 and a[3]>0 and not any(i!=j and contains(b,a)for j,b in enumerate(out))]
fixed=[];moving=[]
for i,b in enumerate(p['blocks']+p.get('blockages',[])):
 w=U(1782.432 if b.get('master')=='col_h10'else b['w']);h=U(b['h'])
 if b['kind']in('phy','ctrl'):fixed.append((i,(U(b['x']),U(b['y']),w+G,h+G)))
 else:moving.append((i,w+G,h+G))
base=[(S,S,R-S+G,T-S+G)]
for i,b in fixed:base=cut(base,b)
start=time.monotonic();best=None;answer=None;attempt=0;rng=random.Random(1021)
# One bounded search; variants are ordering choices of the same constructive algorithm.
while time.monotonic()-start<90:
 free=base[:];positions={i:b for i,b in fixed};left=moving[:]
 mode=attempt%4
 if mode==0:left.sort(key=lambda a:(a[1]*a[2],max(a[1:])) ,reverse=True)
 elif mode==1:left.sort(key=lambda a:(a[2],a[1]),reverse=True)
 elif mode==2:left.sort(key=lambda a:(max(a[1:]),a[1]*a[2]),reverse=True)
 else:left.sort(key=lambda a:a[1]*a[2]*(.75+rng.random()*.5),reverse=True)
 ok=True
 for i,w,h in left:
  candidates=[]
  for x,y,W,H in free:
   if w<=W and h<=H:
    dw,dh=W-w,H-h
    score=(min(dw,dh),max(dw,dh),y,x)if attempt%3 else(W*H-w*h,min(dw,dh),y,x)
    candidates.append((score,(x,y,w,h)))
  if not candidates:ok=False;break
  _,b=min(candidates);positions[i]=b;free=cut(free,b)
 if best is None or len(positions)>best:best=len(positions);print('PACK_PROGRESS',attempt,'placed',best,'of',len(moving)+len(fixed),flush=True)
 attempt+=1
 if ok:answer=positions;break
r={'status':'SAT'if answer else'NO_CONSTRUCTION_WITHIN_BOUND','attempts':attempt,'elapsed_s':time.monotonic()-start,'best_placed':best,'input_sha256':hashlib.sha256((root/'input.json').read_bytes()).hexdigest(),'gap_um':G/1000,'seal_um':100,'die_um':[33000,26000],'scope':'MODEL_ONLY_SOURCE_BODY_PACKING_UNROUTED_UNBOUND','fixed':['PHY','16CTRL'],'relocated':['10SerDes','2reserves'],'source':'91dcb1c93 exact H10wide only; original G8 dimensions otherwise source-model standins'}
if answer:
 q=copy.deepcopy(p);bs=q['blocks']+q.get('blockages',[]);moves=[]
 for i,b in enumerate(bs):
  x,y,w,h=answer[i];old=[b[k]for k in('x','y','w','h')];new=[x/1000,y/1000,(w-G)/1000,(h-G)/1000]
  for k,v in zip(('x','y','w','h'),new):b[k]=v
  if old!=new:moves.append({'name':b['name'],'old':old,'new':new})
 r['moves']=moves;r['frame_count']=sum(b['kind']=='frame'for b in bs);r['logical_links_owed']=len(q['links']);q['links']=[]
 q['facts']={'packing_model':r,'routing_status':'All819 source logical paths must be extracted/repriced. No old relay positions, stages, bandwidth/calendar claims retained.'}
 (root/'maxrects_candidate.json').write_text(json.dumps(q,indent=1)+'\n')
(root/'maxrects_result.json').write_text(json.dumps(r,indent=1)+'\n');print('PACK_RESULT',r['status'],'attempts',attempt,flush=True)
