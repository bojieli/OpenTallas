import json, sys
sys.path.insert(0, sys.path[0])
from common import *
from decomp import BUILDS, D
def man(p, q): return abs(p[0]-q[0]) + abs(p[1]-q[1])
def mst(P):
    n=len(P); inn=[False]*n; dd=[1e18]*n; dd[0]=0; tot=0
    for _ in range(n):
        u=min((i for i in range(n) if not inn[i]), key=lambda i: dd[i]); inn[u]=True; tot+=dd[u]
        for v in range(n):
            if not inn[v]:
                e=man(P[u],P[v])
                if e<dd[v]: dd[v]=e
    return tot
for b,(sp,aj,geo) in BUILDS.items():
    S=parse_spec(sp); sinks,_,_=parse_geo(geo); nets=parse_nets(D+b+"/netcap_TT.txt")
    rr=[]
    for nm,l in S["leaves"].items():
        P=[l["xy"]]+[sinks[r] for r in l["regs"]]
        m=mst(P); cw=nets["ot_ms_%s_clk"%nm]["cw"]; rr.append(cw/m)
    print(b,"leaf nets cw/MST mean %.4f min %.4f max %.4f"%(sum(rr)/len(rr),min(rr),max(rr)))
