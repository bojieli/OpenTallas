"""Finite exact-typed native-site search for independent1-3FF components."""
from pathlib import Path
import json,gzip,collections,math,time
r=Path(__file__).resolve().parent;p=json.load(gzip.open(r/'FINITE_JOINT_PROBLEM.json.gz'));mv=p['movable'];fixed=dict(p['immutable']);adj=collections.defaultdict(set);start=time.time()
for a,b in p['edges']:adj[a].add(b);adj[b].add(a)
seen=set();components=[]
for a in mv:
 if a in seen:continue
 todo=[a];seen.add(a);comp=[]
 while todo:
  f=todo.pop();comp.append(f)
  for n in adj[f]:
   if n in mv and n not in seen:seen.add(n);todo.append(n)
 components.append(comp)
W,H=p['geometry']['actual_core_box_um'][2:];W=round(W*1000);H=round(H*1000);blocked={1080:collections.defaultdict(list),1404:collections.defaultdict(list)}
def forbid_box(x,y,w,h,key):
 # key names record identity for the source packet only; exact strict-overlap intervals.
 for wd,tab in blocked.items():
  lo=math.floor((x-wd/2)/54)+1;hi=math.ceil((x+w+wd/2)/54)-1
  rl=max(0,math.floor((y-270)/270)+1);rh=min(math.floor((H-270)/270),math.ceil((y+h)/270)-1)
  for row in range(rl,rh+1):tab[row].append((lo,hi))
def fixed_box(n):
 x,y=[round(z*1000)for z in n['center_um']];w=round(n['width_um']*1000);forbid_box(x-w/2,y-135,w,270,n['ff'])
for n in fixed.values():fixed_box(n)
for m in p['geometry']['macros']:
 x,y=m['origin_um'];dx,dy=m.get('track_offset_um',[0,0]);x+=dx;y+=dy;w,h=m['outline_um'];z=m['halo_um'];forbid_box(round((x-z)*1000),round((y-z)*1000),round((w+2*z)*1000),round((h+2*z)*1000),m['inst'])
def merge():
 for tab in blocked.values():
  for row,ints in tab.items():
   result=[]
   for lo,hi in sorted(ints):
    if result and lo<=result[-1][1]+1:result[-1]=(result[-1][0],max(result[-1][1],hi))
    else:result.append((lo,hi))
   tab[row]=result
merge()
def candidates(f,assigned,limit=24):
 n=mv[f];lo,hi,vl,vh=[round(x*1000)for x in n['uv_bounds']];wd=round(n['width_um']*1000)
 for other in adj[f]:
  q=assigned.get(other)or(fixed[other]['center_um']if other in fixed else None)
  if q is None:continue
  x,y=[round(z*1000)for z in q];lo=max(lo,x+y-399000);hi=min(hi,x+y+399000);vl=max(vl,x-y-399000);vh=min(vh,x-y+399000)
 if lo>hi or vl>vh:return []
 target=n.get('prior_center_um')or[(lo+hi+vl+vh)/4000,(lo+hi-vl-vh)/4000];tx,ty=[round(x*1000)for x in target]
 rl=max(0,math.ceil(((lo-vh)/2-135)/270));rh=min(math.floor((H-270)/270),math.floor(((hi-vl)/2-135)/270));out=[]
 for row in range(rl,rh+1):
  y=135+270*row;cl=math.ceil(max(wd/2,lo-y,vl+y)/54);ch=math.floor(min(W-wd/2,hi-y,vh+y)/54)
  if cl>ch:continue
  free=[];at=cl
  for a,b in blocked[wd].get(row,[]):
   if b<at:continue
   if a>ch:break
   if a>at:free.append((at,min(a-1,ch)))
   at=max(at,b+1)
   if at>ch:break
  if at<=ch:free.append((at,ch))
  for a,b in free:
   col=min(b,max(a,round(tx/54)));x=col*54
   if any(abs(y-round(v[1]*1000))<270 and abs(x-round(v[0]*1000))<(wd+round(mv[k]['width_um']*1000))/2 for k,v in assigned.items()):continue
   out.append((abs(x-tx)+abs(y-ty),[x/1000,y/1000]))
 return [xy for _,xy in sorted(out)[:limit]]
accepted={};fail=[];large=[];history=[]
for comp in sorted(components,key=lambda c:(len(c),c)):
 if len(comp)>3:large.append(comp);continue
 # Exact native candidates are bounded; an unsuccessful finite search stays HOLD.
 count={f:len(candidates(f,{},24))for f in comp};order=sorted(comp,key=lambda f:count[f]);attempts=[0]
 def search(i,chosen):
  if i==len(order):return chosen
  f=order[i]
  for xy in candidates(f,chosen,24):
   attempts[0]+=1
   if attempts[0]>2000:return None
   result=search(i+1,{**chosen,f:xy})
   if result is not None:return result
  return None
 sol=search(0,{})
 if sol is None:fail.append(dict(component=comp,names=[mv[f]['name']for f in comp],initial_candidate_counts=count,attempts=attempts[0]));continue
 for f,xy in sol.items():
  n=dict(mv[f]);n['center_um']=xy;fixed[f]=n;accepted[f]=xy;fixed_box(n)
 merge();history.append(dict(size=len(comp),attempts=attempts[0]))
summary=dict(status='DECOMPOSED_NATIVE_SITE_SOURCE_PREP_NOT_GLOBAL_PLACEMENT',components=len(components),accepted_tiny_FFs=len(accepted),failed_tiny_components=fail,large_components=[dict(count=len(c),nodes=c)for c in large],elapsed_s=time.time()-start,holds=p['unqualified']);(r/'COMPONENT_SEARCH_SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
with gzip.open(r/'TINY_COMPONENT_SITES.json.gz','wt')as f:json.dump(dict(summary=summary,centers_um=accepted),f,separators=(',',':'))
remaining=set(mv)-set(accepted);out=dict(p);out['movable']={f:mv[f]for f in remaining};out['immutable']=fixed;out['edges']=[e for e in p['edges']if any(f in remaining for f in e)];q=r/'remaining_joint';q.mkdir(exist_ok=True)
with gzip.open(q/'FINITE_JOINT_PROBLEM.json.gz','wt')as f:json.dump(out,f,separators=(',',':'))
print(json.dumps(summary),flush=True)
