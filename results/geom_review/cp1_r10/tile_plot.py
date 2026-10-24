import sys, re, collections
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
R = sys.argv[1]
SEAM = {"col_h10_r0_p1__t1": ("frame_int_o0", "frame_int_i0"), "col_h10_r1__t1": ("frame_int_i1", "frame_int_o1")}
W, H = 1442.88, 1226.88
stats = {}
for k, seam in SEAM.items():
    taps, ff = {}, []
    for ln in open(f"{R}/{k}.ffdump"):
        a = ln.split()
        if a[0] == "TAP":
            taps[a[1]] = (float(a[2]), float(a[3]))
        else:
            ff.append((float(a[1]), float(a[2]), float(a[3]), a[5]))
    cells = np.loadtxt(f"{R}/{k}.ffdump.cells", usecols=(0, 1, 2))
    fig, ax = plt.subplots(1, 3, figsize=(24, 8))
    hb = ax[0].hist2d(cells[:, 0], cells[:, 1], bins=[int(W / 20), int(H / 20)], weights=cells[:, 2] / 400.0,
                      range=[[0, W], [0, H]], cmap="magma", vmax=1.0)
    fig.colorbar(hb[3], ax=ax[0], label="cell area / bin area (20 um bins)")
    ax[0].set_title(f"{k} 4_cts: placement density")
    x = np.array([f[0] for f in ff]); y = np.array([f[1] for f in ff]); a = np.array([f[2] for f in ff])
    isface = np.array([bool(re.match(r"u_(bin|bout)_", f[3])) for f in ff])
    isseam = np.array([any(f[3].startswith(f"u_{d}_{b}/") for b in seam for d in ("bin", "bout")) for f in ff])
    sc = ax[1].scatter(x[~isface], y[~isface], c=a[~isface], s=1, cmap="viridis", vmin=150, vmax=400)
    ax[1].scatter(x[isface], y[isface], c=a[isface], s=6, marker="s", cmap="viridis", vmin=150, vmax=400, edgecolors="none")
    fig.colorbar(sc, ax=ax[1], label="CK rise arrival TT (ps)")
    for n, (tx, ty) in taps.items():
        ax[1].plot(tx, ty, "r*", ms=10); ax[1].annotate(n, (tx, ty), fontsize=7, color="r")
    ax[1].set_title(f"{k}: registers by clock arrival (squares = face flops), taps *")
    for axx in ax[:2]:
        axx.set_xlim(0, W); axx.set_ylim(0, H); axx.set_aspect("equal")
    ax[2].hist(a[isseam], bins=60, alpha=0.7, label=f"seam face flops n={isseam.sum()}")
    ax[2].hist(a[isface & ~isseam], bins=60, alpha=0.5, label=f"other face flops n={(isface & ~isseam).sum()}")
    ax[2].set_xlabel("CK arrival (ps, TT, placement RC)"); ax[2].legend(); ax[2].set_title("face-flop clock arrival")
    fig.tight_layout(); fig.savefig(f"{R}/{k}_tile.png", dpi=70); plt.close(fig)
    s = dict(all_ff=len(a), face=int(isface.sum()), seam=int(isseam.sum()),
             seam_lo=float(a[isseam].min()), seam_hi=float(a[isseam].max()),
             face_lo=float(a[isface].min()), face_hi=float(a[isface].max()),
             seam_p5=float(np.percentile(a[isseam], 5)), seam_p95=float(np.percentile(a[isseam], 95)),
             dens_max_bin=float(hb[0].max()), dens_p99=float(np.percentile(hb[0], 99)))
    stats[k] = s
    print(k, {kk: round(v, 1) if isinstance(v, float) else v for kk, v in s.items()})
