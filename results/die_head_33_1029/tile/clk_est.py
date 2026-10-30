import sys, numpy as np
sys.path.insert(0, sys.argv[1]); import geom_rules as G
D = G.Design(sys.argv[2])
S = np.array([G.ctr(c) for cid, c in D.cells.items() if c[0]=="S" and any(isc for _, isc in D.cell_in.get(cid, []))])
M = [c[2:6] for c in D.cells.values() if c[0]=="M"]
print("sinks", len(S), "macros", len(M), [tuple(round(v,1) for v in m) for m in M])
clear = 8.64
xs = np.arange(8.64, 708.48, 8.64); ys = np.arange(8.64, 1036.8, 8.64)
C = np.array([(x,y) for x in xs for y in ys if not any(m[0]-clear<x<m[2]+clear and m[1]-clear<y<m[3]+clear for m in M)])
def run(R, cap=3000):
    left = np.ones(len(S), bool); E = []
    while left.any():
        U = S[left]; best=None
        for i in range(0, len(C), 1024):
            c = C[i:i+1024]
            cov = ((np.abs(U[:,None,0]-c[None,:,0])+np.abs(U[:,None,1]-c[None,:,1]))<=R).sum(0)
            j = int(cov.argmax())
            if best is None or cov[j]>best[0]: best=(int(cov[j]), tuple(c[j]))
        E.append(best[1]); d=np.abs(S[:,0]-best[1][0])+np.abs(S[:,1]-best[1][1]); left &= d>R
    E=np.array(E); d=np.abs(S[:,None,0]-E[None,:,0])+np.abs(S[:,None,1]-E[None,:,1]); a=d.argmin(1)
    return E, float(d.min(1).max()), np.bincount(a, minlength=len(E))
for R in (180., 200., 210., 220.):
    E, r, ld = run(R)
    print(f"R {R}: {len(E)} entries reach {r:.1f} loads min {ld.min()} max {ld.max()} (cap 3000 {'ok' if ld.max()<=3000 else 'OVER'})")
    if R == 200.: print("  sites", [tuple(map(float, e)) for e in E])
