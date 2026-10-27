import json,sys,collections,statistics as st
B=sys.argv[1]; C=sys.argv[2] if len(sys.argv)>2 else "TT"
P=json.load(open(f"{B}/place.json")); N=json.load(open(f"{B}/nets.json"))["nets"]
arr={}
for l in open(f"{B}/tree_{C}.txt"):
    t=l.split(); arr[t[1]]=(float(t[2]),float(t[3]),float(t[4]))
par={}; netof={}
for n in N:
    for ld in n["loads"]: par[ld]=n["drv"]; netof[ld]=n
def xy(c): p=P.get(c); return (p["x"],p["y"]) if p else None
rows=[]
for d in [c for c in P if c.startswith("ckm_d_")]:
    if d not in arr: continue
    path=[d]; c=d
    while c in par and not par[c].startswith("port:"): c=par[c]; path.append(c)
    wl=0; fo=[]; 
    for a,b in zip(path[:-1],path[1:]):
        A=xy(a);Bb=xy(b)
        n=netof[a]; 
        # net length: star from driver to all loads (Manhattan to this load)
        wl+=abs(A[0]-Bb[0])+abs(A[1]-Bb[1]); fo.append(len(n["loads"]))
    rows.append(dict(d=d,arr=arr[d][0],slew=arr[d][2],st=len(path)-1,wl=wl,fo=tuple(fo[:3]),root=path[-1],x=P[d]["x"],y=P[d]["y"]))
a=[r["arr"] for r in rows]; print(C,"drivers",len(rows),"arr",min(a),max(a),max(a)-min(a))
print("stages",collections.Counter(r["st"] for r in rows)); print("roots",collections.Counter(r["root"] for r in rows))
w=[r["wl"] for r in rows]; print("wl",min(w),max(w))
import numpy as np
X=np.array([[1,r["st"],r["wl"]] for r in rows]); y=np.array(a)
co,res,_,_=np.linalg.lstsq(X,y,rcond=None); pr=X@co; print("fit const,st,wl",co, "resid spread",(y-pr).max()-(y-pr).min(), "rms",np.std(y-pr))
print("fo first3",collections.Counter(r["fo"] for r in rows).most_common(5))
# by stage count
for s in sorted(set(r["st"] for r in rows)):
    aa=[r["arr"] for r in rows if r["st"]==s]; print(" st",s,len(aa),round(min(aa),1),round(max(aa),1))
json.dump(rows,open(sys.argv[3],"w"))
