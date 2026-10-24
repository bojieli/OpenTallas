"""G1 die-plan render: partitions (by type), port windows on faces, lanes with stations, clock taps, spine root,
die channels, and the G0 findings (red outlines).  Called by check.py --png; standalone:

    python3 tools/die_plan/render.py PLAN.json OUT.png
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import schema as S  # noqa: E402


def render(P, geo, R, out_png, title=None):
    import warnings
    warnings.filterwarnings("ignore", message="Unable to import Axes3D")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    W, H = P.W, P.H
    scale = 14.0 / max(W, H)
    fig, ax = plt.subplots(figsize=(max(6.0, W * scale) + 3.2, max(4.0, H * scale) + 0.8), dpi=140)
    cmap = plt.get_cmap("tab20")
    tcol = {t: cmap(i % 20) for i, t in enumerate(sorted(P.types))}
    bad_parts = {i.get("part") for i in (R.errors() if R else []) if i.get("part")}
    bad_ports = {i.get("port") for i in (R.errors() if R else []) if i.get("port")}
    bad_lanes = {i.get("lane") for i in (R.errors() if R else []) if i.get("lane")}
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.2, ec="black"))
    for c in P.die.get("channels", []):
        x0, y0, x1, y1 = P.channel_rect(c)
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="khaki" if "ports" in c else "none", ec="grey",
                               hatch="//", lw=0.4))
    small = len(P.parts) <= 120
    for n, p in P.parts.items():
        x0, y0, x1, y1 = P.rect(n)
        t = P.ptype(n)
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=tcol[p["type"]], alpha=0.35,
                               ec="red" if n in bad_parts else "black", lw=1.4 if n in bad_parts else 0.4))
        for ch in t.get("channels", []):
            a = P.to_die(n, ch["rect_um"][:2])
            b = P.to_die(n, ch["rect_um"][2:])
            ax.add_patch(Rectangle((min(a[0], b[0]), min(a[1], b[1])), abs(b[0] - a[0]), abs(b[1] - a[1]),
                                   fc="none", ec="grey", hatch="..", lw=0.3))
        ck = t.get("clock", {})
        if "tap_um" in ck:
            tx, ty = P.to_die(n, ck["tap_um"])
            ax.plot([tx], [ty], marker="*", ms=6 if small else 3, color="darkorange", zorder=5)
        for tap in ck.get("taps", []):
            tx, ty = P.to_die(n, tap["xy"])
            ax.plot([tx], [ty], marker=".", ms=4 if small else 2, color="purple", zorder=5)
        if small:
            o = P.orient(n)
            ax.text((x0 + x1) / 2, (y0 + y1) / 2, f"{n}\n{p['type']}" + ("" if o == "R0" else f" {o}"),
                    ha="center", va="center", fontsize=6, zorder=6)
    # die IO windows (PLAN-TOOL5 die_io.py): bump fields of the link / HBM PHYs, the host link starred
    for w in P.die.get("io") or []:
        x0, y0, x1, y1 = w["rect_um"]
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="none", ec="magenta", hatch="xx", lw=1.0, zorder=6))
        if w.get("host") or w.get("iface") == "host":
            ax.plot([(x0 + x1) / 2], [(y0 + y1) / 2], marker="H", ms=9, color="magenta", zorder=7)
    root = P.clock.get("spine", {}).get("root_um")
    if root:
        ax.plot([root[0]], [root[1]], marker="P", ms=10, color="crimson", zorder=7)
    # port windows
    from matplotlib.collections import LineCollection
    psegs, pcols = [], []
    for pid, pr in P.ports.items():
        x0, y0, x1, y1 = P.rect(P.face_part(pid))
        lo, hi = sorted(pr["window_um"])
        f = pr["face"]
        pcols.append("red" if pid in bad_ports else "navy")
        if f in "EW":
            x = x1 if f == "E" else x0
            psegs.append([(x, lo), (x, hi)])
        else:
            y = y1 if f == "N" else y0
            psegs.append([(lo, y), (hi, y)])
    ax.add_collection(LineCollection(psegs, linewidths=2.2, colors=pcols, capstyle="butt", zorder=4))
    # lanes
    wmax = max([P.ports[P.lanes[l]["ports"][0]]["width"] for l in P.lanes] + [1])
    from matplotlib.collections import LineCollection
    segs, lws, cols, sx, sy, sc = [], [], [], [], [], []
    for lid, (pts, regs, _) in geo.items():
        w = P.ports[P.lanes[lid]["ports"][0]]["width"]
        col = "red" if lid in bad_lanes else "teal"
        segs.append(pts)
        lws.append(0.3 + 2.0 * (w / wmax) ** 0.5)
        cols.append(col)
        for p in regs[1:-1]:
            sx.append(p[0])
            sy.append(p[1])
            sc.append(col)
    ax.add_collection(LineCollection(segs, linewidths=lws, colors=cols, alpha=0.7, zorder=3))
    ax.scatter(sx, sy, s=4 if len(sx) < 2000 else 1, c=sc, zorder=4, linewidths=0)
    ax.set_xlim(-0.02 * W, 1.02 * W)
    ax.set_ylim(-0.02 * H, 1.02 * H)
    ax.set_aspect("equal")
    ne = len(R.errors()) if R else 0
    ax.set_title(title or f"{P.name}: {len(P.parts)} partitions / {len(P.types)} types, {len(P.ports)} ports, "
                 f"{len(P.lanes)} lanes; G0 {'PASS' if ne == 0 else f'FAIL ({ne} errors)'}", fontsize=9)
    handles = [Rectangle((0, 0), 1, 1, fc=tcol[t], alpha=0.35, ec="black", lw=0.4) for t in sorted(P.types)][:30]
    labels = sorted(P.types)[:30]
    from matplotlib.lines import Line2D
    handles += [Line2D([], [], color="teal", lw=1.5), Line2D([], [], color="teal", marker="o", ls="", ms=3),
                Line2D([], [], color="darkorange", marker="*", ls="", ms=6), Line2D([], [], color="navy", lw=2.2),
                Line2D([], [], color="crimson", marker="P", ls="", ms=8), Line2D([], [], color="red", lw=1.4)]
    labels += ["lane", "station", "clock tap", "port window", "spine root", "G0 error"]
    if P.die.get("io"):
        handles += [Rectangle((0, 0), 1, 1, fc="none", ec="magenta", hatch="xx"),
                    Line2D([], [], color="magenta", marker="H", ls="", ms=7)]
        labels += ["die IO window", "host link"]
    if any(t.get("clock", {}).get("taps") for t in P.types.values()):
        handles.append(Line2D([], [], color="purple", marker=".", ls="", ms=4))
        labels.append("declared clock tap")
    ax.legend(handles, labels, loc="upper left", bbox_to_anchor=(1.01, 1.0), fontsize=6, frameon=False)
    ax.set_xlabel("x (um)", fontsize=7)
    ax.set_ylabel("y (um)", fontsize=7)
    ax.tick_params(labelsize=6)
    fig.tight_layout()
    fig.savefig(out_png)
    plt.close(fig)
    return out_png


if __name__ == "__main__":
    import check
    raw = S.load(sys.argv[1])
    R, _ = check.run(raw, png=sys.argv[2], plan_dir=Path(sys.argv[1]).resolve().parent)   # PLANDIR sidecars (die_io)
    print(sys.argv[2])
