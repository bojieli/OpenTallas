import json, sys
sys.path.insert(0, sys.argv[1])
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import schema as S, die_clock_mesh as DCM
raw = json.load(open(sys.argv[2])); P = S.Plan(raw); cells = json.load(open(sys.argv[3]))
ci = raw["clock"]["mesh"]["core_islands"]
parts = sys.argv[5].split(",")
fig, axs = plt.subplots(1, len(parts), figsize=(7 * len(parts), 7))
for ax, (pn, win) in zip(axs, [(p.split(":")[0], p.split(":")[1]) for p in parts]):
    t = P.ptype(pn); x0, y0, x1, y1 = P.rect(pn)
    ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, ec="k"))
    def box(r, **k):
        a = P.to_die(pn, (r[0], r[1])); b = P.to_die(pn, (r[2], r[3]))
        ax.add_patch(plt.Rectangle((min(a[0], b[0]), min(a[1], b[1])), abs(b[0] - a[0]), abs(b[1] - a[1]), **k))
    for hc in t.get("hard_cores", []):
        box((hc["origin_um"][0], hc["origin_um"][1], hc["origin_um"][0] + hc["outline_um"][0], hc["origin_um"][1] + hc["outline_um"][1]), fill=True, fc="#dde", ec="b", lw=.5)
        for r in ci.get(hc["module"], {}).get("rects_um", []):
            a = DCM.core_frame(P, pn, hc, (r[0], r[1]), inverse=True); b = DCM.core_frame(P, pn, hc, (r[2], r[3]), inverse=True)
            ax.add_patch(plt.Rectangle((min(a[0], b[0]), min(a[1], b[1])), abs(b[0] - a[0]), abs(b[1] - a[1]), fill=False, ec="g", lw=2))
    for r in t.get("clock", {}).get("die_islands_um", []):
        box(r, fill=True, fc="orange", ec="r", lw=.5)
    for n, c in cells.items():
        if x0 <= c["x"] <= x1 and y0 <= c["y"] <= y1:
            ax.add_patch(plt.Rectangle((c["x"], c["y"]), DCM.cell_width(c), 0.27, fc="m", ec="none"))
    wx, wy, ww = map(float, win.split("/"))
    ax.set_xlim(wx - ww, wx + ww); ax.set_ylim(wy - ww, wy + ww); ax.set_aspect("equal")
    ax.set_title(f"{pn} ({t['module']}, orient {P.orient(pn)}): blue=hard core, green=core_islands (12.2a1), orange=partition die_islands, magenta=clock cells", fontsize=7)
fig.savefig(sys.argv[4], dpi=110, bbox_inches="tight")
