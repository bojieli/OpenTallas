"""Diagnostic: classify legal0 failing related pairs (common H-tree prefix, distance, nominal vs early/late) and render."""
import sys, json, re, collections
T, D, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, T)
import numpy as np
import schema as S, die_clock as DC, die_clock_mesh as DM
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P = S.Plan(S.load(f"{D}/../plan.json"))
M = json.load(open(f"{D}/mesh.json"))
xs, ys = np.array(M["xs"]), np.array(M["ys"]); nx, ny = len(xs), len(ys)
tb = collections.defaultdict(list); tap = {}
for t in M["taps"]:
    tb[t["part"]].append(dict(port=t["port"], part=t["part"], xy=t["xy"])); tap[t["port"]] = t
seam = DC.seam_pairs(P, tb)
intra = DC.intra_pairs(tb, float(P.budgets.get("tap_pitch_um", 400.0)))
tagof = {p: DM.htree_tag(int(np.argmin(abs(xs - t["foot"][0]))), int(np.argmin(abs(ys - t["foot"][1]))), nx, ny) for p, t in tap.items()}
res = {}
for corner in ["TT", "FF"]:
    arr = {}
    for l in open(f"{D}/taps_{corner}.txt"):
        f = l.split(); arr[f[1]] = (float(f[2]), float(f[3]))
    rows = []
    for kind, lst in (("seam", [(a, b) for a, b, _ in seam]), ("intra", [(a, b) for a, b, _ in intra])):
        for a, b in lst:
            dm = DC.pair_clock_damage(arr[a][0], arr[a][1], arr[b][0], arr[b][1], 1.0)["max_damage_ps"]
            k = 0
            while k < min(len(tagof[a]), len(tagof[b])) and tagof[a][k] == tagof[b][k]: k += 1
            dist = abs(tap[a]["xy"][0]-tap[b]["xy"][0]) + abs(tap[a]["xy"][1]-tap[b]["xy"][1])
            rows.append(dict(kind=kind, a=a, b=b, dmg=dm, nominal=abs(arr[a][0]-arr[b][0]),
                             el=max(arr[a][0]-arr[a][1], arr[b][0]-arr[b][1]), common_level=k-1, dist=dist))
    bad = [r for r in rows if r["dmg"] > 80]
    lvl = collections.Counter(r["common_level"] for r in bad)
    alll = collections.Counter(r["common_level"] for r in rows)
    by = collections.defaultdict(list)
    for r in rows: by[r["common_level"]].append(r["dmg"])
    res[corner] = dict(pairs=len(rows), fail=len(bad), fail_kinds=dict(collections.Counter(r["kind"] for r in bad)),
                       fail_common_level=dict(sorted(lvl.items())), all_common_level=dict(sorted(alll.items())),
                       max_by_common_level={k: round(max(v), 1) for k, v in sorted(by.items())},
                       fail_dist_um=[round(min(r["dist"] for r in bad), 0), round(max(r["dist"] for r in bad), 0)] if bad else None,
                       fail_nominal_ps=[round(min(r["nominal"] for r in bad), 1), round(max(r["nominal"] for r in bad), 1)] if bad else None,
                       fail_earlylate_ps=[round(min(r["el"] for r in bad), 1), round(max(r["el"] for r in bad), 1)] if bad else None,
                       nominal_all_max=round(max(r["nominal"] for r in rows), 1),
                       worst=[{k: (round(v, 1) if isinstance(v, float) else v) for k, v in r.items()} for r in sorted(bad, key=lambda r: -r["dmg"])[:8]])
    if corner == "TT":
        W, H = M["meta"]["W"], M["meta"]["H"]
        fig, axs = plt.subplots(1, 2, figsize=(16, 19), dpi=110)
        ax = axs[0]
        for n in P.parts:
            r = P.rect(n); ax.add_patch(Rectangle((r[0], r[1]), r[2]-r[0], r[3]-r[1], fill=False, lw=0.3, ec="0.55"))
        for r in DC.keepouts(P):
            ax.add_patch(Rectangle((r[0], r[1]), r[2]-r[0], r[3]-r[1], fc="0.88", ec="none"))
        for g in M["htree"]:
            if g["level"] <= 5:
                ax.plot([g["a"][0], g["b"][0]], [g["a"][1], g["b"][1]], color=plt.cm.viridis(g["level"]/6), lw=3.2-0.45*g["level"])
        late = np.array([arr[p][0] for p in tap]); xy = np.array([tap[p]["xy"] for p in tap])
        sc = ax.scatter(xy[:, 0], xy[:, 1], c=late, s=5, cmap="coolwarm"); plt.colorbar(sc, ax=ax, shrink=0.5, label="tap late arrival TT (ps)")
        for r in bad:
            A, B = tap[r["a"]]["xy"], tap[r["b"]]["xy"]
            ax.plot([A[0], B[0]], [A[1], B[1]], color="red" if r["kind"] == "seam" else "magenta", lw=1.5)
            ax.plot([A[0]], [A[1]], "x", color="k", ms=4)
        for k in range(1, 4):   # H-tree region seams at depth k: draw split lines of the tag prefix grid
            pass
        ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect("equal")
        ax.set_title(f"KV legal0 TT: H-tree L1-5, taps by late arrival, {len(bad)} pairs >80ps (red seam, magenta intra)", fontsize=9)
        ax = axs[1]
        d = np.array([r["dist"] for r in rows]); dm = np.array([r["dmg"] for r in rows]); cl = np.array([r["common_level"] for r in rows])
        sc = ax.scatter(d, dm, c=cl, s=4, cmap="viridis"); plt.colorbar(sc, ax=ax, label="deepest common H-tree level of feeding drivers")
        ax.axhline(80, color="r"); ax.set_xlabel("tap-tap Manhattan distance (um)"); ax.set_ylabel("related-pair damage, root-only CPPR (ps)")
        ax.set_title("damage vs distance (TT)", fontsize=9)
        fig.tight_layout(); fig.savefig(OUT); plt.close(fig)
json.dump(res, open(OUT.replace(".png", ".json"), "w"), indent=1)
for c, r in res.items(): print(c, json.dumps({k: v for k, v in r.items() if k != "worst"})); print(json.dumps(r["worst"][:4]))
