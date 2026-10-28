import json,sys,collections
d=sys.argv[1]
t=json.load(open(d+"/tree.json"))
po=t["parent_of"];S=t["sites"]
print("meta",t["meta"])
keys=[k for k in po if k not in S][:3];print("non-site keys",len([k for k in po if k not in S]),keys)
arr={}
for l in open(d+"/arr_TT.txt"):
    f=l.split()
    if f[0]=="T": arr[f[1]]=(float(f[2]),float(f[3]))
print(len(arr), list(arr)[:2])
def xy(k):
    return S[k]
rows=[]
tapxy={}
for tp in t["taps"]: tapxy[tp["port"]]=tp
# tap ports in arr may include _tN suffix; find their parent
miss=0
for p,(a,b) in arr.items():
    if p not in tapxy: miss+=1;continue
    tp=tapxy[p]; k=t["node_buf"][str(tp["node"])]; x0,y0=tp["xy"]; x1,y1=S[k]; L=abs(x1-x0)+abs(y1-y0); x0,y0=x1,y1; n=1
    while k in po:
        q=po[k]; x1,y1=S[q]; L+=abs(x1-x0)+abs(y1-y0); x0,y0=x1,y1; k=q; n+=1
    rows.append((p,a,b,L/1000,n))
print("miss",miss,len(rows))
import statistics as st
# least squares a*L + b*n + c
import itertools
def lsq(rows,ix):
    import numpy as np
    A=np.array([[r[3],r[4],1] for r in rows]);y=np.array([r[ix] for r in rows])
    c,res,_,_=np.linalg.lstsq(A,y,rcond=None); e=y-A@c
    return c,abs(e).max(),e.std()
for ix,nm in ((1,"TT"),(2,"FF")):
    c,mx,sd=lsq(rows,ix); print(nm,"ps/mm=%.1f ps/stage=%.1f c=%.0f  maxerr=%.0f sd=%.0f"%(c[0],c[1],c[2],mx,sd))
Ls=[r[3] for r in rows];ns=[r[4] for r in rows]
print("L mm min/max",min(Ls),max(Ls),"stages",min(ns),max(ns))
