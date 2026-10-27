import sys, json
sys.path.insert(0, sys.argv[1])
import qc_clk_mesh3 as Q3
from collections import defaultdict, Counter
class A: pass
a=A(); a.r2=sys.argv[2]
rec, P, dtp, parts, cores, cols, gaps, rows, m, dy = Q3.lattice(a)
bt=defaultdict(list)
for n in P.parts: bt[P.parts[n]["type"]].append(n)
W=max(P.rect(n)[2] for n in P.parts); H=max(P.rect(n)[3] for n in P.parts)
print("die",W,H, "area cover", sum((P.rect(n)[2]-P.rect(n)[0])*(P.rect(n)[3]-P.rect(n)[1]) for n in P.parts)/(W*H))
for t in ["cbx_q10","cbf_q00","cbf_q01","cbn_q00"]:
    print(t, sorted({(round(P.rect(n)[1],1),P.parts[n].get('orient','R0')) for n in bt[t]}))
# who is at x0 0, 777.6
for n in P.parts:
    r=P.rect(n)
    if r[0]<1500: print("west",n,P.parts[n]["type"],[round(v,1) for v in r])
# missing cbf_q00 position: partitions in row y0 2617.92 even positions
for n in P.parts:
    r=P.rect(n)
    if abs(r[1]-2617.92)<1 or abs(r[1]-0)<1:
        if P.parts[n]["type"] not in ("cbx_q10","cbf_q00","cbf_q01","cbf_q11"): print("rowodd",n,P.parts[n]["type"],[round(v,1) for v in r])
cen=[n for n in P.parts if 10000<P.rect(n)[1]<15800]
print("central parts",len(cen))
c=Counter(P.parts[n]["type"] for n in cen)
print("central types",len(c),"single-inst", sum(1 for t in c if len(bt[t])==1), sorted(Counter(len(bt[t]) for t in c).items()))
print("rows central y0:",sorted(Counter(round(P.rect(n)[1],1) for n in cen).items()))
print("rows all y0:",sorted(Counter((round(P.rect(n)[1],1),round(P.rect(n)[3]-P.rect(n)[1],1)) for n in P.parts).items()))
