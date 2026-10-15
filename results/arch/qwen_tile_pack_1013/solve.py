import numpy as np,json
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.sparse import lil_matrix
r=[]
for k,n,w,h in [('bank',5,1440,600),('lane',8,462,650),('node',1,220,2000),('tx',8,120,400),('rqr',2,1440,100),('ctl',1,220,1500),('cache_ASSUMED',1,220,1000)]:
 for i in range(n):r.append((f'{k}{i}',w,h))
n=len(r);pairs=[(i,j)for i in range(n)for j in range(i+1,n)];nv=2*n+4*len(pairs);W=1680;H=6600;gap=93;margin=93
rows=[];low=[];high=[]
def add(d,l=-np.inf,u=np.inf):rows.append(d);low.append(l);high.append(u)
for p,(i,j)in enumerate(pairs):
 b=2*n+4*p;wi,hi=r[i][1:];wj,hj=r[j][1:]
 add({i:1,j:-1,b:-W},u=-wi-gap)
 add({j:1,i:-1,b+1:-W},u=-wj-gap)
 add({n+i:1,n+j:-1,b+2:-H},u=-hi-gap)
 add({n+j:1,n+i:-1,b+3:-H},u=-hj-gap)
 add({b:1,b+1:1,b+2:1,b+3:1},u=3)
for i in range(n-1):
 if r[i][0].rstrip('0123456789')==r[i+1][0].rstrip('0123456789'):add({n+i:1,n+i+1:-1},u=0)
a=lil_matrix((len(rows),nv))
for i,d in enumerate(rows):
 for j,v in d.items():a[i,j]=v
lb=np.r_[np.full(2*n,margin),np.zeros(4*len(pairs))];ub=np.r_[[W-margin-z[1]for z in r],[H-margin-z[2]for z in r],np.ones(4*len(pairs))]
c=np.zeros(nv);c[:2*n]=.001
res=milp(c,integrality=np.ones(nv),bounds=Bounds(lb,ub),constraints=LinearConstraint(a.tocsr(),low,high),options={'time_limit':45,'mip_rel_gap':1})
out={'status':res.status,'message':res.message,'qualified':False,'assumptions':{'outline':[362.88,1425.6],'between_children':20.088,'outer_margin':20.088,'ctl':[47.52,324],'cache_unmeasured':[47.52,216]},'rects':[]}
if res.x is not None:
 for i,z in enumerate(r):out['rects'].append({'name':z[0],'x':round(res.x[i]*.216,3),'y':round(res.x[n+i]*.216,3),'w':z[1]*.216,'h':z[2]*.216})
print(json.dumps(out,indent=2));open(__file__.replace('solve.py','fixed_shapes_bound.json'),'w').write(json.dumps(out,indent=2)+'\n')
