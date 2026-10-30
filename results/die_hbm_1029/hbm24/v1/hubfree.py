"""hub hard-core occupancy + free-rectangle search (grid 8.64 um) for the V1h SFU-into-hub estimate; also renders PNG.
usage: hubfree.py PLAN TYPE OUT_PNG"""
import json, sys
import numpy as np
P = json.load(open(sys.argv[1])); t = P["partition_types"][sys.argv[2]]
W, H = t["outline_um"]; g = 8.64
nx, ny = int(W / g) + 1, int(H / g) + 1
occ = np.zeros((ny, nx), bool)
HALO = 8.64
for h in t["hard_cores"]:
    (x, y), (w, hh) = h["origin_um"], h["outline_um"]
    occ[max(0, int((y - HALO) / g)):int((y + hh + HALO) / g) + 1, max(0, int((x - HALO) / g)):int((x + w + HALO) / g) + 1] = True
free = (~occ).sum() * g * g
print("hub", W, H, "free area mm2 %.2f of %.2f" % (free / 1e6, W * H / 1e6))
# largest empty rectangles of given sizes: count placements of 388.8x345.6 lane cores greedily
def fits(w, h):
    a, b = int(np.ceil(w / g)), int(np.ceil(h / g))
    S = np.zeros((ny + 1, nx + 1), int); S[1:, 1:] = occ.cumsum(0).cumsum(1)
    s = S[b:, a:] - S[:-b, a:] - S[b:, :-a] + S[:-b, :-a]
    return np.argwhere(s == 0)
for (w, h) in [(388.8, 345.6), (669.6, 626.4), (760.32, 691.2), (1857.6, 1572.48), (1209.6, 1572.48), (1700, 1100), (2200, 900)]:
    f = fits(w, h)
    print("rect %7.1f x %7.1f fits at %d grid spots" % (w, h, len(f)), "e.g." if len(f) else "", [(round(x * g), round(y * g)) for y, x in f[:: max(1, len(f) // 4)][:4]])
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(14, 7.5))
ax.imshow(occ, origin="lower", extent=[0, W, 0, H], cmap="Greys", alpha=0.6)
for h in t["hard_cores"]:
    (x, y), (w, hh) = h["origin_um"], h["outline_um"]
    c = "red" if "sfu" in h["inst"] else "blue"
    ax.add_patch(plt.Rectangle((x, y), w, hh, fill=False, ec=c, lw=0.6))
ax.set_title(f"{sys.argv[2]} hard cores (red = sfu*), grey = core+halo; free {free/1e6:.2f} mm2")
fig.savefig(sys.argv[3], dpi=90, bbox_inches="tight")
