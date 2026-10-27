#!/usr/bin/env python3
"""KV-PLAN-EVAL hub_Ei: per-bit vertical demand map + render (event plan, sited slots)."""
import json, sys, collections
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
P = json.load(open(sys.argv[1])); tn = sys.argv[2]; out = sys.argv[3]
t = P["partition_types"][tn]; W, H = t["outline_um"]
DX, DY = 5.0, 5.0
nx, ny = int(W // DX) + 1, int(H // DY) + 1
V = np.zeros((ny, nx))   # vertical bits crossing each 5x5 cell
segs = []
for s in t["ft_slots"]:
    r = s.get("regs_um"); bs = s.get("bit_sites_um")
    if not r or not bs: continue
    w = int(s["width"])
    segs.append((s["name"], w, r))
    for k in range(len(bs) - 1):
        A, B = bs[k], bs[k + 1]
        for b in range(w):
            a, c = A[b % len(A)], B[b % len(B)]
            if abs(a[1] - c[1]) < DY: continue
            x = c[0]  # H-then-V
            j = min(int(x // DX), nx - 1)
            i0, i1 = sorted((int(a[1] // DY), int(c[1] // DY)))
            V[i0:i1, j] += 1
    # in-pin leg / out-pin leg not modelled (face pins: horizontal for E/W faces)
cap_per_um = 32 * 0.6       # GEOM-24 sizing: 32 vertical tracks/um (M5+M7) x 0.6 cut_avail
res = {}
for win in (15, 30, 60, 120):
    k = int(win // DX)
    cs = np.cumsum(np.pad(V, ((0, 0), (1, 0))), axis=1)
    S = cs[:, k:] - cs[:, :-k]
    i, j = np.unravel_index(np.argmax(S), S.shape)
    res[f"{win}um"] = dict(max_bits=int(S[i, j]), x0=j * DX, y=i * DY, capacity_bits=round(cap_per_um * win),
                           demand_ratio=round(S[i, j] / (cap_per_um * win) * 0.6, 2))
# columns over capacity at 15 um
k = 3; cs = np.cumsum(np.pad(V, ((0, 0), (1, 0))), axis=1); S = cs[:, k:] - cs[:, :-k]
over = sorted({int(j * DX) for i, j in zip(*np.where(S > cap_per_um * 15))})
res["x_over_cap_15um"] = over
print(json.dumps(res, indent=1))
fig, ax = plt.subplots(1, 2, figsize=(16, 11), gridspec_kw=dict(width_ratios=[1.3, 1]))
im = ax[0].imshow(V, origin="lower", extent=[0, nx * DX, 0, ny * DY], cmap="magma", vmax=max(1, V.max()))
plt.colorbar(im, ax=ax[0], label="vertical FT bits crossing (5x5 um cell)")
for name, w, r in segs:
    xs, ys = zip(*r)
    ax[0].plot(xs, ys, "-", color="cyan", lw=0.3 + 2.5 * min(1, w / 1118), alpha=0.6)
    ax[0].plot(xs[1:], ys[1:], ".", color="lime", ms=2)
ax[0].add_patch(plt.Rectangle((0, 0), W, H, fill=False, ec="white", lw=1))
ax[0].set_title(f"{tn} event 3cb5395c6: FT station paths (cyan, width~bits) + per-bit vertical demand")
ax[0].set_xlabel("x um"); ax[0].set_ylabel("y um")
peak = V.max(axis=0)
k = 3; prof = np.convolve(peak, np.ones(k), "same")
ax[1].plot(np.arange(nx) * DX, prof, color="k", lw=1, label="max over y of vertical bits in 15-um window (approx)")
ax[1].axhline(cap_per_um * 15, color="r", ls="--", label=f"15-um capacity {cap_per_um*15:.0f} bits (32 tr/um x 0.6)")
ax[1].set_xlabel("x um"); ax[1].set_ylabel("bits"); ax[1].legend(loc="upper right", fontsize=8)
ax[1].set_title("column demand vs capacity")
plt.tight_layout(); plt.savefig(out, dpi=110)
json.dump(res, open(out.replace(".png", ".json"), "w"), indent=1)
