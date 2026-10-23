#!/usr/bin/env python3
"""Render a kit's floorplan PLAN (outline, hard children with their LEF pin faces after orientation, top pin ranges,
face fences) for the GEOM-REVIEW before any P&R.  usage: plan_render.py <spec.json> <out.png> [fence.tcl]"""
import json, os, re, sys, collections
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.patches as P
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
def lef_faces(path):
    t = open(path).read(); m = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", t); W, H = float(m.group(1)), float(m.group(2))
    c = collections.Counter()
    for pm in re.finditer(r"\n\s*PIN\s+(\S+)(.*?)\n\s*END\s+\1", t, re.S):
        if re.search(r"USE\s+(POWER|GROUND)", pm.group(2)): continue
        r = re.search(r"RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)", pm.group(2))
        if not r: continue
        x = (float(r.group(1)) + float(r.group(3))) / 2; y = (float(r.group(2)) + float(r.group(4))) / 2
        d = {"W": x, "E": W - x, "S": y, "N": H - y}; c[min(d, key=d.get)] += 1
    return W, H, c
ROT = {"R0": {}, "MX": {"N": "S", "S": "N"}, "MY": {"W": "E", "E": "W"}, "R180": {"N": "S", "S": "N", "W": "E", "E": "W"},
       "R90": {"N": "W", "W": "S", "S": "E", "E": "N"}, "R270": {"N": "E", "E": "S", "S": "W", "W": "N"}}
def main():
    spec = json.load(open(sys.argv[1])); out = sys.argv[2]
    W, H = spec["outline"]["w"], spec["outline"]["h"]
    fig, ax = plt.subplots(figsize=(9, 9 * H / W))
    ax.add_patch(P.Rectangle((0, 0), W, H, fc="#111", ec="w"))
    if len(sys.argv) > 3:
        t = open(sys.argv[3]).read(); bands = re.search(r"set ot_r6_bands \{(.*)\}\n", t).group(1)
        for b in re.findall(r"\{(\S+) ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)\}", bands):
            n, x0, y0, x1, y1 = b[0], *map(float, b[1:])
            if n == "core": continue
            ax.add_patch(P.Rectangle((x0, y0), x1 - x0, y1 - y0, fc="#2e8b57", alpha=.35, ec="#3cb371", lw=1, ls="--"))
            ax.text(x0 + 2, y0 + 2, n, color="#9f9", fontsize=7)
    hard = 0
    for c in spec.get("children", []) + spec.get("macros", []):
        v = c["view"]; n = v.rstrip("/").split("/")[-1]
        lw, lh, faces = lef_faces(os.path.join(ROOT, v, n + ".lef"))
        o = c.get("orient", "R0"); w, h = (lh, lw) if o in ("R90", "R270") else (lw, lh)
        x, y = c["at"]; hard += w * h
        ax.add_patch(P.Rectangle((x, y), w, h, fc="#4a90d9", ec="white", lw=.8, alpha=.85))
        tot = sum(faces.values()) or 1
        for f, k in faces.items():
            g = ROT.get(o, {}).get(f, f); th = 2 + 10 * k / tot
            seg = {"N": (x, y + h - th, w, th), "S": (x, y, w, th), "W": (x, y, th, h), "E": (x + w - th, y, th, h)}[g]
            ax.add_patch(P.Rectangle(seg[:2], seg[2], seg[3], fc="#ffcc00", ec="none", alpha=.9))
        ax.text(x + w / 2, y + h / 2, "%s\n%s %s" % (c.get("inst", n).split(".")[-1], n.replace("ot_hbm_", "").replace("ot_", ""), o),
                ha="center", va="center", fontsize=6, color="k")
    face_of = {p: f for f, ps in spec["pins"].items() for p in ps}
    for p, (a, b) in (spec.get("pin_ranges") or {}).items():
        f = face_of.get(p)
        if f is None: continue
        seg = {"N": ([a, b], [H, H]), "S": ([a, b], [0, 0]), "W": ([0, 0], [a, b]), "E": ([W, W], [a, b])}[f]
        ax.plot(*seg, color="cyan", lw=4, solid_capstyle="butt")
        tx, ty = (sum(seg[0]) / 2, sum(seg[1]) / 2)
        ax.text(tx, ty, p, color="cyan", fontsize=6, rotation=90 if f in "WE" else 0,
                ha="right" if f == "W" else "left" if f == "E" else "center", va="top" if f == "S" else "bottom" if f == "N" else "center")
    ax.set_xlim(-60, W + 60); ax.set_ylim(-40, H + 40); ax.set_aspect("equal")
    ax.set_title("%s PLAN %.1f x %.1f um = %.3f mm2, hard children %.1f%% (yellow = child pin faces, cyan = top pin ranges, green = face fences)"
                 % (spec["name"], W, H, W * H / 1e6, 100 * hard / (W * H)), fontsize=8)
    plt.savefig(out, dpi=90, bbox_inches="tight"); print(out)
if __name__ == "__main__":
    main()
