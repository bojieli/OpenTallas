import json, sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
R = Path(sys.argv[0]).resolve().parents[3]; sys.path[:0] = [str(R/"tools/die_plan"), str(R/"tools/s81_head")]
import head_band_ringff_delta as H, clock_landing_plan as CLP
old, new, tn, png = json.load(open(sys.argv[1])), json.load(open(sys.argv[2])), sys.argv[3], sys.argv[4]
to, t = old["partition_types"][tn], new["partition_types"][tn]
fig, ax = plt.subplots(figsize=(6, 11)); w, h = t["outline_um"]
ax.add_patch(Rectangle((0, 0), w, h, fill=False, lw=1.5))
for r, n in H.core_rects(t, False) + H.core_rects(t, True):
    ax.add_patch(Rectangle(r[:2], r[2]-r[0], r[3]-r[1], color="0.75"))
for s in t.get("ft_slots", []):
    for st in s.get("bit_sites_um", []) or []:
        if st: xs=[p[0] for p in st]; ys=[p[1] for p in st]; ax.add_patch(Rectangle((min(xs),min(ys)),max(xs)-min(xs)+.5,max(ys)-min(ys)+.5,color="tab:green",alpha=.5))
for b, v in to["clock"]["landing_contract"]["bands"].items():
    r = v["rect_um"]; ax.add_patch(Rectangle(r[:2], r[2]-r[0], r[3]-r[1], fill=False, ls="--", ec="tab:red", lw=1))
for b, v in t["clock"]["landing_contract"]["bands"].items():
    r = v["rect_um"]; ax.add_patch(Rectangle(r[:2], r[2]-r[0], r[3]-r[1], color="tab:blue", alpha=.45)); ax.text(r[0], r[1], b, fontsize=5)
for r in CLP.reset_site_rects(t["clock"]["landing_contract"].get("collector_tree")):
    ax.add_patch(Rectangle(r[:2], r[2]-r[0], r[3]-r[1], color="tab:purple"))
ax.set_xlim(-10, w+10); ax.set_ylim(-10, h+10); ax.set_aspect("equal")
ax.set_title(f"{tn}\nred dashed = plan_qc48 bands, blue = plan_qc49 (ring_ff x2, ff), grey ROM, purple reset boxes, green FT", fontsize=7)
fig.savefig(png, dpi=110, bbox_inches="tight")
