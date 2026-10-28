"""render the built die clock tree (die_trial tree.json): feed legs blue, region-tree legs green, legs > 450 um red,
partitions grey; usage: ctree_pil.py TREE PLAN OUT"""
import json, sys
from PIL import Image, ImageDraw
t = json.load(open(sys.argv[1])); p = json.load(open(sys.argv[2])); out = sys.argv[3]
N = {n["id"]: n for n in t["nodes"].values()}
W, H = p["die"]["outline_um"]; S = 2400 / W; Ht = int(H * S) + 60
im = Image.new("RGB", (2420, Ht), "white"); dr = ImageDraw.Draw(im)
P = lambda x, y: (10 + x * S, Ht - 10 - y * S)
T = p["partition_types"]
for q in p["partitions"]:
    x, y = q["origin_um"]; w, h = T[q["type"]]["outline_um"]
    dr.rectangle([P(x, y + h), P(x + w, y)], outline=(170, 170, 170))
n_long = 0; segs = {"o": [], "rt": [], "feed": [], "long": []}
for n in N.values():
    if n["parent"] is None: continue
    a = N[n["parent"]]; L = abs(a["x"] - n["x"]) + abs(a["y"] - n["y"])
    k = "long" if L > 450 else ("feed" if n.get("feed") else ("rt" if n.get("rtree") or n.get("region") else "o"))
    segs[k].append(((a["x"], a["y"]), (n["x"], n["y"])))
for k, c, w in (("o", (150, 150, 150), 1), ("rt", (0, 150, 0), 1), ("feed", (0, 0, 230), 2), ("long", (230, 0, 0), 3)):
    for (a, b) in segs[k]: dr.line([P(*a), P(*b)], fill=c, width=w)
dr.text((10, 5), f"S81 DIE-S81-14 go14 built local clock (link_htree + region DME early MERGE, inv2, feed sb6): feed blue {len(segs['feed'])}, region trees green {len(segs['rt'])}, other grey {len(segs['o'])}, legs>450um red {len(segs['long'])}", fill="black")
im.save(out); print({k: len(v) for k, v in segs.items()})
