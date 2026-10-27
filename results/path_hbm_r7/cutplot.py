import json, sys
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, sys.argv[3])
import plan_cut as PC
P = json.load(open(sys.argv[1])); T = P["partition_types"]
fig, axs = plt.subplots(2, 2, figsize=(14, 8))
def prof(t, relaxed):
    W, H = t["outline_um"]; nets = PC._nets(t); cores = PC._cores(t)
    if relaxed: nets = PC._relax(W, H, nets, cores)
    X = np.arange(4.32, W - 1e-6, 4.32); Y = np.arange(4.32, H - 1e-6, 4.32)
    dx = np.zeros(len(X)); dy = np.zeros(len(Y))
    for n in nets:
        xs=[p[0] for p in n["pts"]]; ys=[p[1] for p in n["pts"]]
        dx[(X>min(xs))&(X<max(xs))]+=n["bits"]; dy[(Y>min(ys))&(Y<max(ys))]+=n["bits"]
    bx=np.zeros(len(X)); by=np.zeros(len(Y))
    if not relaxed:
        for (x0,y0,x1,y1) in cores.values():
            bx[(X>x0)&(X<x1)]+=y1-y0; by[(Y>y0)&(Y<y1)]+=x1-x0
    cx=(H-np.minimum(bx,H))*0.75/0.048+H*0.75/0.064; cy=(W-np.minimum(by,W))*0.75/0.048+W*0.75/0.064
    return X, dx/cx, Y, dy/cy, cores, W, H
for col, tn in enumerate(["q_hub_nw", "q_b102"]):
    t = T[tn]
    X, ux, Y, uy, cores, W, H = prof(t, False)
    Xr, uxr, Yr, uyr, _, _, _ = prof(t, True)
    a = axs[0][col]
    a.plot(X, ux, label="vertical cuts (x), current plan b1e2"); a.plot(Xr, uxr, label="x, relaxed WL-optimal re-pack (lower bound)")
    a.plot(Y if False else [], [])
    a.axhline(0.6, color="r", ls="--", label="gate 0.6"); a.set_title(f"{tn} {W}x{H} um: bits across x-cuts / M4+M6 tracks"); a.set_xlabel("x um"); a.set_ylabel("cut use"); a.legend(fontsize=7)
    a = axs[1][col]
    a.plot(Y, uy, label="horizontal cuts (y), current"); a.plot(Yr, uyr, label="y, relaxed re-pack")
    a.axhline(0.6, color="r", ls="--"); a.set_title(f"{tn}: bits across y-cuts / M5+M7 tracks"); a.set_xlabel("y um"); a.legend(fontsize=7)
fig.suptitle("PATH-HBM-R7 cut lower bound (tree-aware, plan_cut.py) on plan_b1e2 81f5433b - UNCHECKED")
fig.tight_layout(); fig.savefig(sys.argv[2], dpi=90)
