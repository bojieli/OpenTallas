import sys, json
sys.path.insert(0, sys.argv[1])
import qc_clk_mesh3 as Q3
from collections import defaultdict
class A: pass
a=A(); a.r2=sys.argv[2]
rec, P, dtp, parts, cores, cols, gaps, rows, m, dy = Q3.lattice(a)
print("cols",len(cols),cols[:6],"...",cols[-3:])
print("gaps",gaps)
print("rows",len(rows), "m",m,"dy",dy)
bt=defaultdict(list)
for n in P.parts: bt[P.parts[n]["type"]].append(n)
xs=sorted({round(P.rect(n)[0],2) for n in P.parts}); ys=sorted({round(P.rect(n)[1],2) for n in P.parts})
print("nparts",len(P.parts),"ntypes",len(bt))
print("distinct x0",len(xs),xs[:40]); print("distinct y0",len(ys),ys[:60])
for t,ins in sorted(bt.items(), key=lambda kv:-len(kv[1]))[:20]:
    r=[P.rect(n) for n in ins]
    print(t,len(ins),"w,h",round(r[0][2]-r[0][0],2),round(r[0][3]-r[0][1],2),"x0s",sorted({round(q[0],1) for q in r})[:12],"y0s",sorted({round(q[1],1) for q in r})[:30], "orients",sorted({P.parts[n].get('orient','R0') for n in ins}))
# gaps between partitions in x: union of x-intervals
iv=sorted((P.rect(n)[0],P.rect(n)[2]) for n in P.parts)
print("cores",len(cores), cores[0])
