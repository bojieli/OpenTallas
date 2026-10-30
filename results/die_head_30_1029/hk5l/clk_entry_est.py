import sys, json, numpy as np
sys.path.insert(0, sys.argv[1])
import geom_rules as G
D = G.Design(sys.argv[2])
S = []
for cid, c in D.cells.items():
    if c[0] == "S" and any(isc for _, isc in D.cell_in.get(cid, [])):
        S.append(G.ctr(c))
S = np.array(S); print("sinks", len(S))
def reach(E):
    E = np.array(E); d = np.abs(S[:, None, 0] - E[None, :, 0]) + np.abs(S[:, None, 1] - E[None, :, 1])
    b = d.min(1); return float(b.max()), float(np.percentile(b, 99)), float(np.percentile(b, 50))
for nm, E in [("cur (354.24,354.24)", [(354.24, 354.24)]), ("(354,717)", [(354.24, 717.12)]), ("centre (354,518)", [(354.24, 518.4)])]:
    print(nm, "max/p99/p50", [round(x, 1) for x in reach(E)])
# grid of candidate entries on the street/channel lattice: k-center greedy (Gonzalez) then local check vs 200
for R in (200.0, 220.0):
    left = np.ones(len(S), bool); E = []
    while left.any():
        # choose the candidate grid point covering most uncovered sinks within R
        xs = np.arange(8.64, 708.48, 17.28); ys = np.arange(8.64, 1036.8, 17.28)
        C = np.array([(x, y) for x in xs for y in ys])
        U = S[left]
        best = None
        for i in range(0, len(C), 512):
            c = C[i:i + 512]
            cov = ((np.abs(U[:, None, 0] - c[None, :, 0]) + np.abs(U[:, None, 1] - c[None, :, 1])) <= R).sum(0)
            j = int(cov.argmax())
            if best is None or cov[j] > best[0]: best = (int(cov[j]), tuple(c[j]))
        E.append(best[1])
        d = np.abs(S[:, 0] - best[1][0]) + np.abs(S[:, 1] - best[1][1])
        left &= d > R
    print(f"R {R}: {len(E)} entries", [tuple(round(v, 1) for v in e) for e in E], "reach", [round(x, 1) for x in reach(E)])
