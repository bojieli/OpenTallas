"""G1 die-plan render: partitions (by type), port windows on faces, lanes with stations, clock taps, spine root,
die channels, and the G0 findings (red outlines).  Called by check.py --png; standalone:

    python3 tools/die_plan/render.py PLAN.json OUT.png [--pre PRE.json|PRE.log]
    python3 tools/die_plan/render.py PLAN.json OUT_DIR --types a,b      per-type mode = render_type_heat.py (one PNG per type)

R6-RENDER-LEGEND-STREET (VIS-REOWN 11-25, COORD): the legend lists EVERY type, numbered; each partition carries its type number when the
die is too dense for names.  Stations draw above clock taps (hollow taps), so a tap never hides a station.  The title never says
"G0 PASS" alone: it gives the G0 error/warning counts as "G0 only" plus the PRE / static class FAIL counts (plan_gate_pre --json output
or its log, --pre / pre=), or says PRE was not supplied.
"""
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import schema as S  # noqa: E402
import gen_phys  # noqa: E402


def pre_counts(src):
    """PRE / static findings -> (Counter{class: FAIL findings}, advisories) or None.  src: plan_gate_pre --json record (dict or path),
    or its text log (lines 'FAIL <CLASS> ...', 'WARN ADV...').  Class = the word after FAIL, cut at the first '-' (as PLAN-GATE-PRE
    classes=... does)."""
    if src is None:
        return None
    if isinstance(src, dict):
        lines = list(src.get("findings") or []) + list(src.get("advisories") or [])
    else:
        try:
            txt = Path(src).read_text(errors="replace")
        except OSError:
            return None
        try:
            rec = json.loads(txt)
            lines = list(rec.get("findings") or []) + list(rec.get("advisories") or [])
        except ValueError:
            lines = txt.splitlines()
    c, adv = Counter(), 0
    for ln in lines:
        w = str(ln).split()
        if len(w) >= 2 and w[0] == "FAIL":
            c[w[1].split("-")[0]] += 1
        elif len(w) >= 2 and w[0] == "WARN" and w[1].startswith("ADV"):
            adv += 1
    return c, adv


def status_title(P, R, pre=None):
    """'G0 only: N errors / M warnings | PRE FAIL k classes: GEOM 12, TOOLS 3' -- never a bare 'G0 PASS'"""
    ne = len(R.errors()) if R else 0
    nw = sum(1 for i in R.items if i.get("level") == "WARN") if R else 0
    g0 = f"G0 only: {ne} errors / {nw} warnings" if R else "G0 not run"
    pc = pre_counts(pre)
    if pc is None:
        ps = "PRE/static not supplied (G0 alone is not a plan PASS)"
    elif not pc[0]:
        ps = "PRE/static PASS (0 FAIL classes" + (f", {pc[1]} advisories)" if pc[1] else ")")
    else:
        ps = f"PRE/static FAIL {len(pc[0])} classes: " + ", ".join(f"{k} {v}" for k, v in pc[0].most_common())
    return f"{g0} | {ps}"


def type_colors(types):
    """distinct colours for many types: tab20 + tab20b + tab20c (60), then cycled; the type NUMBER disambiguates beyond that"""
    import matplotlib.pyplot as plt
    pal = [plt.get_cmap(m)(i) for m in ("tab20", "tab20b", "tab20c") for i in range(20)]
    return {t: pal[i % len(pal)] for i, t in enumerate(sorted(types))}


def render(P, geo, R, out_png, title=None, extra=None, view=None, pre=None):
    import warnings
    warnings.filterwarnings("ignore", message="Unable to import Axes3D")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    W, H = P.W, P.H
    scale = 14.0 / max(W, H)
    tnames = sorted(P.types)
    tnum = {t: k + 1 for k, t in enumerate(tnames)}
    leg_cols = max(1, -(-(len(tnames) + 10) // 48))          # every type in the legend, 48 rows per column
    fig, ax = plt.subplots(figsize=(max(6.0, W * scale) + 1.2 + 2.0 * leg_cols, max(4.0, H * scale) + 0.8), dpi=140)
    tcol = type_colors(tnames)
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
        # Render the same complete, snapped R4 grid + sink taps as the kit.
        # tap_um alone is only the root-nearest reference point, not its CTS inputs.
        clock_xy = [P.to_die(n, (x, y)) for _, x, y in gen_phys.clock_pins(P, p["type"])]
        if clock_xy:            # hollow, under the stations (zorder 3.5 < stations 6): a tap never hides a station
            tx, ty = zip(*clock_xy)
            ax.plot(tx, ty, marker="*", ls="", ms=6 if small else 3, mfc="none", mec="darkorange", mew=0.6, zorder=3.5)
        for tap in ck.get("taps", []):
            tx, ty = P.to_die(n, tap["xy"])
            ax.plot([tx], [ty], marker="o", ms=3 if small else 1.5, mfc="none", mec="purple", mew=0.5, zorder=3.5)
        if small:
            o = P.orient(n)
            ax.text((x0 + x1) / 2, (y0 + y1) / 2, f"{n}\n{tnum[p['type']]} {p['type']}" + ("" if o == "R0" else f" {o}"),
                    ha="center", va="center", fontsize=6, zorder=7)
        else:
            ax.text((x0 + x1) / 2, (y0 + y1) / 2, str(tnum[p["type"]]), ha="center", va="center", fontsize=3.5, zorder=7, alpha=0.8)
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
    ax.scatter(sx, sy, s=5 if len(sx) < 2000 else 1.5, c=sc, zorder=6, linewidths=0)
    if extra:
        extra(ax)                  # SEAM-HOP-1: caller overlay (seam_hop_render.py); default None = unchanged
    ax.set_xlim(*(view[0] if view else (-0.02 * W, 1.02 * W)))
    ax.set_ylim(*(view[1] if view else (-0.02 * H, 1.02 * H)))
    ax.set_aspect("equal")
    ax.set_title(title or f"{P.name}: {len(P.parts)} partitions / {len(P.types)} types, {len(P.ports)} ports, "
                 f"{len(P.lanes)} lanes; {status_title(P, R, pre)}", fontsize=9)
    from matplotlib.lines import Line2D
    handles = [Line2D([], [], color="teal", lw=1.5), Line2D([], [], color="teal", marker="o", ls="", ms=3),
               Line2D([], [], marker="*", ls="", ms=6, mfc="none", mec="darkorange"), Line2D([], [], color="navy", lw=2.2),
               Line2D([], [], color="crimson", marker="P", ls="", ms=8), Line2D([], [], color="red", lw=1.4)]
    labels = ["lane", "station (drawn above taps)", "clock tap (hollow)", "port window", "spine root", "G0 error"]
    if P.die.get("io"):
        handles += [Rectangle((0, 0), 1, 1, fc="none", ec="magenta", hatch="xx"),
                    Line2D([], [], color="magenta", marker="H", ls="", ms=7)]
        labels += ["die IO window", "host link"]
    if any(t.get("clock", {}).get("taps") for t in P.types.values()):
        handles.append(Line2D([], [], marker="o", ls="", ms=4, mfc="none", mec="purple"))
        labels.append("declared clock tap")
    handles += [Rectangle((0, 0), 1, 1, fc=tcol[t], alpha=0.35, ec="black", lw=0.4) for t in tnames]       # ALL types, numbered
    labels += [f"{tnum[t]} {t}" for t in tnames]
    ax.legend(handles, labels, loc="upper left", bbox_to_anchor=(1.01, 1.0), fontsize=5 if len(tnames) > 40 else 6, frameon=False,
              ncol=leg_cols, columnspacing=0.8, handlelength=1.2)
    ax.set_xlabel("x (um)", fontsize=7)
    ax.set_ylabel("y (um)", fontsize=7)
    ax.tick_params(labelsize=6)
    fig.tight_layout()
    fig.savefig(out_png)
    plt.close(fig)
    try:                    # machine-readable record of what the PNG shows (reviewers and tests read it)
        Path(str(out_png) + ".json").write_text(json.dumps(dict(
            title=ax.get_title(), types=len(tnames), legend_types=[l for l in labels if l.split(" ", 1)[0].isdigit()],
            legend_columns=leg_cols, zorder=dict(station=6, clock_tap=3.5, type_number=7), pre=status_title(P, R, pre)), indent=1) + "\n")
    except OSError:
        pass
    return out_png


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("out", help="OUT.png (die render) or OUT_DIR with --types")
    ap.add_argument("--pre", help="plan_gate_pre --json record or log: PRE / static class FAIL counts in the title")
    ap.add_argument("--types", help="per-type mode: comma list (or 'all') -> render_type_heat.py, one PNG per type in OUT_DIR")
    a = ap.parse_args(argv)
    if a.types:
        import render_type_heat
        return render_type_heat.main([a.plan, a.out] + ([] if a.types == "all" else ["--types", a.types]))
    import check
    raw = S.load(a.plan)
    R, _ = check.run(raw, png=a.out, plan_dir=Path(a.plan).resolve().parent, pre=a.pre)   # PLANDIR sidecars (die_io)
    print(a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
