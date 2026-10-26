"""render the proof-leaf density tap plan of each pair type (type frame): sinks, taps (load), radius, reset relays,
old grid taps (x)."""
import json, sys
sys.path.insert(0, sys.argv[1])
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle
import schema as S, taps as TP, gen_phys, reset_tree as RT, pair
raw = json.load(open(sys.argv[2])); old = json.load(open(sys.argv[3])); outd = sys.argv[4]
P = S.Plan(raw); PO = S.Plan(old)
for tn, t in P.types.items():
    w, h = t["outline_um"]
    pts = TP.sink_sites(P, tn)
    tp = TP.density_taps(P, tn)
    load, far, asg = TP.assign([(n, x, y) for n, x, y, _, _ in tp], pts, int(t["clock"]["tap_max_sinks"]), 100.0, 100.0)
    rel = RT.for_type(P, tn)["relays"]
    grid = S.tap_grid(PO, tn)
    for zoom in (None, (0, 0, 420, 140), (0, h - 140, 420, h)):
        fig, ax = plt.subplots(figsize=(14, 12 if zoom is None else 6), dpi=110)
        ax.add_patch(Rectangle((0, 0), w, h, fill=False, lw=1.5))
        cols = plt.get_cmap("tab20")
        for (x, y, n), j in zip(pts, asg):
            ax.scatter([x], [y], s=4 + 2.5 * min(n, 60), color=cols(j % 20), alpha=.6, lw=0)
        for (x, y, n), j in zip(pts, asg):
            ax.plot([x, tp[j][1]], [y, tp[j][2]], color=cols(j % 20), lw=.3, alpha=.4)
        for gn, gx, gy in grid:
            ax.plot(gx, gy, "x", color="0.6", ms=7)
        for r in rel:
            ax.plot(*r["xy"], "s", ms=3, mfc="none", mec="k", mew=.6)
        for j, (n, x, y, s, rr) in enumerate(tp):
            ax.add_patch(Polygon([(x - 100, y), (x, y + 100), (x + 100, y), (x, y - 100)], fill=False, ls=":", lw=.5, ec=cols(j % 20)))
            ax.plot(x, y, "^", ms=9, color=cols(j % 20), mec="k")
            ax.annotate(f"{n}\n{int(load[j])}", (x, y), fontsize=6 if zoom is None else 8, xytext=(3, 3), textcoords="offset points")
        if zoom:
            ax.set_xlim(zoom[0], zoom[2]); ax.set_ylim(zoom[1], zoom[3])
        else:
            ax.set_xlim(-20, w + 20); ax.set_ylim(-20, h + 20)
        ax.set_aspect("equal")
        mx = max(load)
        ax.set_title(f"{tn} proof-leaf density taps: {len(tp)} taps (^, label port/sinks), max {int(mx)} sinks/tap, "
                     f"max sink->tap {max(far):.0f} um (<=100 diamond); {int(sum(load))} sinks; reset relays sq ({len(rel)}); "
                     f"old grid x ({len(grid)})", fontsize=9)
        sfx = "" if zoom is None else ("_zS" if zoom[1] == 0 else "_zN")
        fig.tight_layout(); fig.savefig(f"{outd}/{tn}_taps{sfx}.png"); plt.close(fig)
    print(tn, len(tp), int(max(load)), round(max(far), 1), len(rel))
