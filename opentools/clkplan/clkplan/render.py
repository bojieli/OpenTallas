"""Plan render: macros (grey; red = beyond street reach), streets (green), tree legs (blue; red = blocked),
unplaced nodes (red x), failing crossings (magenta)."""
import numpy as np


def render(P, res, T, S, png):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    from matplotlib.patches import Rectangle
    W, H = P["die"]["w"], P["die"]["h"]
    fig, ax = plt.subplots(figsize=(12, 12 * H / W + 1.0))
    if S is not None:
        g = S.g
        img = np.zeros(S.net.shape + (4,))
        img[S.net] = (0.6, 0.88, 0.6, 1.0)
        ax.imshow(img, origin="lower", extent=(0, S.net.shape[1] * g, 0, S.net.shape[0] * g), interpolation="nearest")
        bad = {w["name"] for w in res["streets"]["worst"]}
    else:
        bad = set()
    for m in P["macros"]:
        r = m["rect"]
        c = "#d62728" if m["name"] in bad else ("#9a9a9a" if m["kind"] == "hard_core" else "#6a6aa0")
        ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc=c, ec="k", lw=0.2, alpha=0.85))
    ok, blk = [], []
    for lg in T.legs:
        a, b = T.cells[lg["parent"]]["xy"], T.cells[lg["child"]]["xy"]
        m = (b[0], a[1]) if lg["route"] == "x_first" else (a[0], b[1])
        segs = [(a, m), (m, b)]
        (blk if any(x[2] > T.cfg["leg_max_um"] for x in lg["blocked"]) else ok).extend(segs)
    ax.add_collection(LineCollection(ok, colors="#1f4fbf", linewidths=0.5))
    ax.add_collection(LineCollection(blk, colors="#e00000", linewidths=2.0))
    for u in T.unplaced:
        ax.plot([u["ideal"][0]], [u["ideal"][1]], "rx", ms=7, mew=2)
    by = {s["name"]: s for s in T.sinks}
    bad_x = [r for r in res["crossings"]["rows"] if "error" not in r and not r["pass"]]
    for r in bad_x[:200]:
        a, b = by[r["a"]]["xy"], by[r["b"]]["xy"]
        ax.plot([a[0], b[0]], [a[1], b[1]], "-", color="#d000d0", lw=1.0)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.set_aspect("equal")
    t = res["tree"]
    ax.set_title(f"{res['plan']}: {res['verdict']} | {t['levels']} lv, {t['repeaters']} reps, red legs = "
                 f"{t['blocked_legs']} blocked, x = {t['unplaced']} unplaced, magenta = {len(bad_x)} crossings < "
                 f"{res['crossings']['summary']['min_margin_ps']} ps", fontsize=9)
    fig.tight_layout()
    fig.savefig(png, dpi=110)
    plt.close(fig)
