"""R13 render + identity record of the periodic top tree (legal cells after assign_periodic). UNCHECKED."""
import sys, json
sys.path.insert(0, "/w/die_plan")
import qc_clk_mesh3 as M
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
out = sys.argv[1]
ap = M.argparse.ArgumentParser(); M.add_common(ap)
a = ap.parse_args("--r2 inputs/r2_plan_w.json --stage inputs/stage_table.json --no-spine --top-w 16w --top-m 2 --top-reach 450 --islands type --feed periodic".split())
st = M.Stage(a.stage); B = M.build(a, st)
cells, ls = M.legalize(B); B["cells"] = cells
PE = M.phys_edges(B)
P = B["P"]
isl = ls["islands"]
json.dump(dict(label="UNCHECKED", periodic=B["periodic"], islands=isl, legal={k: v for k, v in ls.items() if k != "islands"}),
          open(out + "/r13_identity.json", "w"), indent=1, default=str)
def draw(path, box, title):
    fig, ax = plt.subplots(figsize=(16, 13.5) if box is None else (12, 10), dpi=110)
    for n in P.parts:
        r = P.rect(n)
        ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fill=False, lw=0.3, ec="#888"))
        if box is not None and box[0] < r[0] < box[2] and box[1] < r[1] < box[3]:
            ax.text(r[0] + 5, r[1] + 5, f"{P.parts[n]['type']} {P.parts[n].get('orient','R0')}", fontsize=6, color="#555")
    for c in B["cores"]:
        ax.add_patch(Rectangle((c[0], c[1]), c[2] - c[0], c[3] - c[1], fc="#f2d7d5", ec="none"))
    for (ns, tag), legs in PE.items():
        if ns != "t":
            continue
        colr = "#c0392b" if tag.startswith("H") else ("#1f4e9c" if tag.startswith("T") else "#2e8b57")
        for a_, b_, L in legs:
            ax.plot([a_["site"][0], b_["site"][0]], [a_["site"][1], b_["site"][1]], lw=0.8 if box else 0.4, c=colr)
    for k, cl, s in (("top_node", "#d62728", 6), ("top_rep", "#333", 3), ("col_tap", "#ff7f0e", 6), ("chan_node", "#8e44ad", 8), ("chan_rep", "#8e44ad", 4)):
        xs = [c["site"][0] for c in cells if c["kind"] == k]; ys = [c["site"][1] for c in cells if c["kind"] == k]
        ax.scatter(xs, ys, s=s * (3 if box else 1), c=cl, label=f"{k} ({len(xs)})", zorder=3)
    if box:
        ax.set_xlim(box[0], box[2]); ax.set_ylim(box[1], box[3])
    else:
        ax.set_xlim(0, float(P.W)); ax.set_ylim(0, float(P.H))
    ax.set_aspect("equal"); ax.legend(loc="upper right", fontsize=8); ax.set_title(title, fontsize=9)
    fig.savefig(path, bbox_inches="tight"); plt.close(fig)
t = f"R13 periodic top tree: channel x-tree (purple/red, die-level centre channel) + per-period y-trees (blue M9) + local x-trees (green M8); types identical {isl['types_identical']}/{isl['types_hosting']} UNCHECKED"
draw(out + "/r13_top.png", None, t)
draw(out + "/r13_zoom_cb.png", (3800, 1000, 9200, 10600), "R13 zoom: periods 1-2, bottom cb rows 1-4 (cbx rows 2+4 MX host the same local rows)")
draw(out + "/r13_zoom_centre.png", (11500, 9800, 17500, 16500), "R13 zoom: die centre, channel line y=13132.8 + mirrored half trees")
print("ok")
