# Joint shared-master orientation/face feasibility: no new types or signal cycles.
import json,sys,pathlib,shutil,re,itertools,collections,math,numpy as np
src,out,rp,tools=sys.argv[1:]; src,out=pathlib.Path(src),pathlib.Path(out)
shutil.copytree(src,out,symlinks=False,ignore=shutil.ignore_patterns('gates'))
sys.path.insert(0,tools);import check as C,schema as S
d=json.loads((out/'die_plan.json').read_text());T=d['partition_types'];D={};last={}
oldbf=C.best_face;oldwarn=C.FACE_WARN_COS;oldaway=C.FACE_AWAY_COS
C.FACE_WARN_COS=C.FACE_AWAY_COS=1e9
def bf(dirs):last['d']=list(dirs);return oldbf(dirs)
C.best_face=bf
class Rep(C.Report):
 def err(self,check,msg,**kw):
  super().err(check,msg,**kw);self.items[-1]['dirs']=last.get('d')
r=Rep(True);C.check_core_faces(S.Plan(d,out/'die_plan.json'),r,str(out),None,max_msgs=10**9)
for x in r.errors():
 m=re.match(r'type (\S+) core (\S+) port (\S+): (\d+) pins on face (\S+) face away',x['msg'])
 if m:D[(m[1],m[2],m[3])]=(int(m[4]),x.get('dirs') or [])
C.best_face=oldbf;C.FACE_WARN_COS=oldwarn;C.FACE_AWAY_COS=oldaway
OR=('R0','MX','MY','R180');FS=('N','S','E','W');norm=dict(N=(0,1),S=(0,-1),E=(1,0),W=(-1,0))
def tf(o,f):
 if o in ('MX','R180') and f in 'NS':f={'N':'S','S':'N'}[f]
 if o in ('MY','R180') and f in 'EW':f={'E':'W','W':'E'}[f]
 return f
def orient(o,x,y,w,h):return (w-x if o in ('MY','R180') else x,h-y if o in ('MX','R180') else y)
by=collections.defaultdict(list)
for tn,t in T.items():
 for h in t.get('hard_cores',[]):by[h.get('pins_file')].append((tn,h))
report=[]
for pf,users in by.items():
 if not pf:continue
 ports=sorted({p for tn,h in users for t,c,p in D if (t,c)==(tn,h['inst'])})
 if not ports:continue
 entries=[]
 for p in ports:
  obs=[]
  for idx,(tn,h) in enumerate(users):
   q=D.get((tn,h['inst'],p))
   if q and q[1]:obs.append((idx,q))
  entries.append((p,obs))
 cur=tuple(h.get('orient','R0') for tn,h in users)
 # Only change a master when existing orientations make some port impossible on every single shared face.
 # Precompute exact per-instance cost of every possible master face and orientation.
 bits=np.zeros((len(entries),len(users),4,4),dtype=np.int64)
 groups=np.zeros_like(bits)
 for pp,(p,obs) in enumerate(entries):
  for i,(n,dirs) in obs:
   for oi,o in enumerate(OR):
    for fi,F in enumerate(FS):
     nx,ny=norm[tf(o,F)];bad=max(nx*x+ny*y for _,x,y in dirs)<-1e-9
     bits[pp,i,oi,fi]=n*bad;groups[pp,i,oi,fi]=bad
 def objective(os):
  ix=np.array([OR.index(o) for o in os]);u=np.arange(len(users));b=bits[:,u,ix,:].sum(axis=1);g=groups[:,u,ix,:].sum(axis=1)
  v=b*(len(users)+1)+g;k=v.argmin(axis=1);rr=np.arange(len(entries))
  return int(b[rr,k].sum()),int(g[rr,k].sum()),sum(a!=b for a,b in zip(os,cur))
 initial=objective(cur)
 if initial[0]==0:continue
 if len(users)<=4:
  best=min(itertools.product(OR,repeat=len(users)),key=objective)
 else:
  candidates=[]
  for seed in [cur,tuple('R0' for _ in users),tuple('MY' for _ in users)]:
   os=list(seed)
   for iteration in range(8):
    previous=tuple(os)
    for ii in range(len(users)):
     choices=[tuple(os[:ii]+[o]+os[ii+1:]) for o in OR];os=list(min(choices,key=objective))
    if tuple(os)==previous:break
   candidates.append(tuple(os))
  best=min(candidates,key=objective)
 goal=objective(best)
 if goal[:2]>=initial[:2]:continue
 changes=[]
 for (tn,h),old,new in zip(users,cur,best):
  if old==new:continue
  inst=h['inst'];base=re.sub('__q[0-9]+$','',inst);x0,y0=h['origin_um'];w,hh=h['outline_um'];t=T[tn]
  def trans(p):
   x,y=orient(old,p[0]-x0,p[1]-y0,w,hh);x,y=orient(new,x,y,w,hh);return [round(x+x0,6),round(y+y0,6)]
  ends=0
  for s in t.get('internal_stations',[]):
   for sk,pk in [('launch','from_um'),('capture','to_um')]:
    name=str(s.get(sk,''));pt=s[pk]
    match=name==inst or name.startswith(inst+'.') or name==base or name.startswith(base+'.')
    if match and x0-0.1<=pt[0]<=x0+w+0.1 and y0-0.1<=pt[1]<=y0+hh+0.1:s[pk]=trans(pt);ends+=1
  for tap in t.get('clock',{}).get('taps',[]):
   if tap['name']==inst or tap['name'].startswith(inst+'.'):tap['xy']=trans(tap['xy'])
  h['orient']=new;changes.append(dict(type=tn,inst=inst,old=old,new=new,endpoints=ends))
 report.append(dict(table=pf,before=initial,after=goal,changes=changes));print(pf,initial,'->',goal,flush=True)
(out/'die_plan.json').write_text(json.dumps(d,indent=1)+'\n');pathlib.Path(rp).write_text(json.dumps(report,indent=1)+'\n')
