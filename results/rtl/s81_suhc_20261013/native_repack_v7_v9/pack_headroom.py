import json,sys,numpy as np,time
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.sparse import lil_matrix
p=json.load(open('pack_input.json'));ls=p['instances'];n=len(ls);ids={x['instance']:i for i,x in enumerate(ls)};pairs=[(i,j) for i in range(n) for j in range(i)];nv=2*n+2+4*len(pairs);H=2*n;E=H+1
c=np.zeros(nv);c[H]=1;c[E]=10000
lb=np.zeros(nv);ub=np.ones(nv)*1200;ub[H]=840.24;ub[E]=1000;lb[E]=-300
width=float(sys.argv[1]) if len(sys.argv)>1 else 575.992
for i,l in enumerate(ls):ub[2*i]=width-l['outline_um'][0];ub[2*i+1]=1200-l['outline_um'][1]
ub[0]=0;ub[1]=0
integrality=np.zeros(nv)
for k in range(2*n+2,nv):ub[k]=1;integrality[k]=1
rows=[];upp=[]
def row(d,v):rows.append(d);upp.append(v)
for i,l in enumerate(ls):row({2*i+1:1,H:-1},-l['outline_um'][1])
for z in p['constraints']:
 a=ids[z['a']];b=ids[z['b']];sx=z['sx'];sy=z['sy'];row({2*a:sx,2*a+1:sy,2*b:-sx,2*b+1:-sy,E:-1},z['ub'])
M=2400;gap=8.64
for k,(i,j) in enumerate(pairs):
 b=2*n+2+4*k;wi,hi=ls[i]['outline_um'];wj,hj=ls[j]['outline_um']
 row({2*i:1,2*j:-1,b:M},M-wi-gap);row({2*j:1,2*i:-1,b+1:M},M-wj-gap)
 row({2*i+1:1,2*j+1:-1,b+2:M},M-hi-gap);row({2*j+1:1,2*i+1:-1,b+3:M},M-hj-gap)
 row({b:-1,b+1:-1,b+2:-1,b+3:-1},-1)
A=lil_matrix((len(rows),nv))
for k,d in enumerate(rows):
 for v,x in d.items():A[k,v]=x
res=milp(c,integrality=integrality,bounds=Bounds(lb,ub),constraints=LinearConstraint(A.tocsr(),np.full(len(rows),-np.inf),np.array(upp)),options={'time_limit':120,'mip_rel_gap':.001})
out=dict(status=str(res.message),width=width,objective=res.fun,best_bound=res.get('mip_dual_bound'),gap=res.get('mip_gap'),scope=p['status'])
if res.x is not None:out.update(height=float(res.x[H]),extra_reach_um=float(res.x[E]),placements={l['instance']:[float(res.x[2*i]),float(res.x[2*i+1])] for i,l in enumerate(ls)})
json.dump(out,open('pack_headroom_result.json','w'),indent=2);print(json.dumps(out,indent=2))
