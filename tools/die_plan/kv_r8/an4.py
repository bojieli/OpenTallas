import json,sys,collections,re,numpy as np
B=sys.argv[1]; C=sys.argv[2]
P=json.load(open(f"{B}/place.json")); N=json.load(open(f"{B}/nets.json"))["nets"]; M=json.load(open(f"{B}/mesh.json"))
arr={l.split()[1]:float(l.split()[2]) for l in open(f"{B}/tree_{C}.txt")}
par={}; net={}
for n in N:
    for ld in n["loads"]: par[ld]=n["drv"]; net[ld]=n
def xy(c): return (P[c]["x"],P[c]["y"])
rows=[]
for d in arr:
    if not d.startswith("ckm_d_"): continue
    p=par[d]; n=net[d]; A=xy(p); D=xy(d)
    L=abs(A[0]-D[0])+abs(A[1]-D[1]); tot=sum(abs(A[0]-xy(x)[0])+abs(A[1]-xy(x)[1]) for x in n["loads"])
    rows.append((arr[d]-arr[p],L,tot,len(n["loads"]),p,arr[p]))
r=np.array([[a,b,c] for a,b,c,*_ in rows])
print("drv leg delay",r[:,0].min(),r[:,0].max(),"len",r[:,1].min(),r[:,1].max(),"net star len",r[:,2].min(),r[:,2].max())
X=np.c_[np.ones(len(r)),r[:,1],r[:,2]]; co=np.linalg.lstsq(X,r[:,0],rcond=None)[0]; res=r[:,0]-X@co
print("fit",co,"resid spread",res.max()-res.min())
print("fanout",collections.Counter(x[3] for x in rows))
# driver slides from mesh.json drivers
dv=M["drivers"]; k=list(dv)[0]; print("driver entry",k,str(dv[k])[:400])
# total delay vs (L10 node arrival, drv leg)
a=np.array([x[5] for x in rows]); t=a+r[:,0]; print("corr node arr vs leg", np.corrcoef(a,r[:,0])[0,1], "spread node",a.max()-a.min(),"total",t.max()-t.min())
