import json,sys,time
import numpy as np
from scipy.sparse import coo_matrix
from scipy.optimize import linprog, milp, Bounds, LinearConstraint
from scipy.sparse import hstack,vstack
D=json.load(open('graph.json'));xy=np.array(D['xy']);N=len(xy);face=set(D['face']);limit=float(sys.argv[1]) if len(sys.argv)>1 else 395
mode=sys.argv[2] if len(sys.argv)>2 else'free'
if len(sys.argv)>3 and sys.argv[3]=='separate_reset':
 root=next(i for i,n in enumerate(D['cells']) if n=='u_g.g_rst_native.q$_DFF_P_');D['edges']=[(i,j) for i,j in D['edges'] if i!=root];mode+='_reset_separate'
row=[];col=[];val=[];b=[]
def add(terms,rhs):
 r=len(b);b.append(rhs)
 for c,v in terms:row.append(r);col.append(c);val.append(v)
for i,j in D['edges']:
 for a,c in ((1,1),(1,-1),(-1,1),(-1,-1)):add([(i,a),(j,-a),(N+i,c),(N+j,-c)],limit)
for i,(x,y) in enumerate(xy):
 add([(i,1),(2*N+i,-1)],x);add([(i,-1),(2*N+i,-1)],-x)
 add([(N+i,1),(3*N+i,-1)],y);add([(N+i,-1),(3*N+i,-1)],-y)
bounds=[(4.8,453.1)]*N+[(4.8,1152.9)]*N+[(0,None)]*(2*N)
# Restrict to the existing unobstructed vertical/horizontal placement street.
# This is an estimate only; actual legalizer and exact geometry must pass later.
if mode.startswith('streets'):
 for i,(x,y) in enumerate(xy):
  if i in face:continue
  rects=[]
  # Maximal vertical corridor at current x, allowing x motion only until the nearest macro edge.
  lower,upper=4.8,1152.9;xl,xh=4.8,453.1
  for a,c,e,f in D['macros']:
   if a-1<x<e+1:
    if f<y:lower=max(lower,f+1)
    elif c>y:upper=min(upper,c-1)
   if f+1>lower and c-1<upper:
    if e<x:xl=max(xl,e+1)
    elif a>x:xh=min(xh,a-1)
  if xl<=x<=xh and lower<=y<=upper:rects.append((xl,xh,lower,upper))
  # Horizontal street analogue.
  lower,upper=4.8,453.1;yl,yh=4.8,1152.9
  for a,c,e,f in D['macros']:
   if c-1<y<f+1:
    if e<x:lower=max(lower,e+1)
    elif a>x:upper=min(upper,a-1)
   if e+1>lower and a-1<upper:
    if f<y:yl=max(yl,f+1)
    elif c>y:yh=min(yh,c-1)
  if lower<=x<=upper and yl<=y<=yh:rects.append((lower,upper,yl,yh))
  if rects:
   a,e,c,f=max(rects,key=lambda r:max(r[1]-r[0],r[3]-r[2]));bounds[i]=(a,e);bounds[N+i]=(c,f)
for i in face:
 for x,y,name in D['face_ports'][str(i)]:
  budget=145 if ('rst' in name or 't_out[512]'==name or 't_out[513]'==name) else 30
  for a,c in ((1,1),(1,-1),(-1,1),(-1,-1)):add([(i,a),(N+i,c)],budget+a*x+c*y)
A=coo_matrix((val,(row,col)),shape=(len(b),4*N)).tocsc();cost=np.r_[np.zeros(2*N),np.ones(2*N)]
print('LP',N,len(b),A.nnz,'limit',limit,mode,flush=True);t=time.time();r=linprog(cost,A_ub=A,b_ub=b,bounds=bounds,method='highs');print('RESULT',r.success,r.message,'seconds',time.time()-t,flush=True)
out=dict(success=r.success,message=r.message,limit=limit,mode=mode)
if r.success:
 new=np.c_[r.x[:N],r.x[N:2*N]];moves=np.abs(new-xy).sum(axis=1);out.update(objective=r.fun,moved=int((moves>.1).sum()),maxmove=float(moves.max()),positions=new.tolist());print('MOVED',out['moved'],'max',out['maxmove'],flush=True)
json.dump(out,open('solution_'+mode+'.json','w'))
if mode.startswith('free') and r.success and len(sys.argv)>4 and sys.argv[4]=='legal':
 pairs=set();iteration=0
 while True:
  new=np.c_[r.x[:N],r.x[N:2*N]]
  bad={(i,k) for i,(x,y) in enumerate(new) for k,(a,b_,c,d) in enumerate(D['macros']) if a-.4<x<c+.4 and b_-.2<y<d+.2}
  fresh=bad-pairs
  print('MACRO iteration',iteration,'bad',len(bad),'new',len(fresh),flush=True)
  if not bad:
   out.update(positions=new.tolist(),macro_clear=True,iterations=iteration);json.dump(out,open('solution_legal.json','w'));break
  if not fresh:raise RuntimeError('No progress in macro disjunction separation')
  pairs|=fresh;iteration+=1;ar=[];ac=[];av=[];bb=[];nvar=4*N+4*len(pairs)
  def cut(terms,rhs):
   rr=len(bb);bb.append(rhs)
   for j,v in terms:ar.append(rr);ac.append(j);av.append(v)
  for z,(i,k) in enumerate(sorted(pairs)):
   a,b_,c,d=D['macros'][k];zz=4*N+4*z;M=2400
   cut([(i,1),(zz,-M)],a-.8);cut([(i,-1),(zz+1,-M)],-c-.8)
   cut([(N+i,1),(zz+2,-M)],b_-.4);cut([(N+i,-1),(zz+3,-M)],-d-.4)
   cut([(zz+t,1) for t in range(4)],3)
  AA=vstack([hstack([A,coo_matrix((A.shape[0],nvar-4*N))]),coo_matrix((av,(ar,ac)),shape=(len(bb),nvar))]).tocsc()
  lows=np.array([q[0] for q in bounds]+[0]*(nvar-4*N));highs=np.array([q[1] if q[1] is not None else np.inf for q in bounds]+[1]*(nvar-4*N))
  print('MILP',iteration,len(pairs),'pairs',nvar,'variables',flush=True)
  r=milp(np.r_[cost,np.zeros(nvar-4*N)],integrality=np.r_[np.zeros(4*N),np.ones(nvar-4*N)],bounds=Bounds(lows,highs),constraints=LinearConstraint(AA,-np.inf,np.r_[b,bb]))
  print('MILP RESULT',r.success,r.message,flush=True)
  if not r.success:break

