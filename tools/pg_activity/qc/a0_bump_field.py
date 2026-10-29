#!/usr/bin/env python3
"""QC-PG-5 (OWNER 10-28 option c): write the QC plan PG delta = 75-um power-bump field over the A0 array incl. streets.
Field = union of the 768 A0 core outlines (qfd_tile_n[kl]_a0c, plan census) dilated by DIL um (QC-PG-4 solve: 155),
merged into rectangles; base 150/70, field 75/37.5, keep 75 (QC-PG-4 MEp75 rule: base bumps >= 75 um from field bumps);
M9 width .672 (QC-PG-MAP/QC-PG-4 solve deck).  usage: a0_bump_field.py PLAN.json OUT_PLAN.json [DIL]"""
import json, sys, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "die_plan"))
src, dst = sys.argv[1], sys.argv[2]
DIL = float(sys.argv[3]) if len(sys.argv) > 3 else 155.0
P = json.load(open(src))
pt = P["partition_types"]
A0 = ("qfd_tile_nk_a0c", "qfd_tile_nl_a0c")


def xf(o, orient, W, H, r):
    x0, y0, x1, y1 = r
    if orient in ("MY", "R180"): x0, x1 = W - x1, W - x0
    if orient in ("MX", "R180"): y0, y1 = H - y1, H - y0
    return [o[0] + x0, o[1] + y0, o[0] + x1, o[1] + y1]


a0 = []
for q in P["partitions"]:
    t = pt[q["type"]]; W, H = t["outline_um"]; seen = set()
    for key in ("hard_cores", "contents"):
        for c in t.get(key, []):
            if c.get("module") not in A0 or c.get("origin_um") is None or c["inst"] in seen: continue
            seen.add(c["inst"])
            r = [c["origin_um"][0], c["origin_um"][1], c["origin_um"][0] + c["outline_um"][0], c["origin_um"][1] + c["outline_um"][1]]
            a0.append(xf(q["origin_um"], q.get("orient", "R0"), W, H, r))
DW, DH = P["die"]["outline_um"]
dil = [[max(0, r[0] - DIL), max(0, r[1] - DIL), min(DW, r[2] + DIL), min(DH, r[3] + DIL)] for r in a0]
# exact union -> rectangles: sweep over the distinct y breakpoints, merge x intervals per band, then merge equal bands
ys = sorted({v for r in dil for v in (r[1], r[3])})
bands = []
for y0, y1 in zip(ys, ys[1:]):
    iv = sorted((r[0], r[2]) for r in dil if r[1] <= y0 and r[3] >= y1)
    m = []
    for a, b in iv:
        if m and a <= m[-1][1] + 1e-6: m[-1][1] = max(m[-1][1], b)
        else: m.append([a, b])
    bands.append((y0, y1, [tuple(round(v, 3) for v in x) for x in m]))
rects = []
open_ = {}
for y0, y1, m in bands:
    nxt = {}
    for iv in m:
        if iv in open_: nxt[iv] = (open_[iv][0], y1)
        else: nxt[iv] = (y0, y1)
    for iv, (a, b) in open_.items():
        if iv not in nxt: rects.append([iv[0], round(a, 3), iv[1], round(b, 3)])
    open_ = nxt
rects += [[iv[0], round(a, 3), iv[1], round(b, 3)] for iv, (a, b) in open_.items()]
rects.sort(key=lambda r: (r[1], r[0]))
area = sum((r[2] - r[0]) * (r[3] - r[1]) for r in rects) * 1e-6
pg = P["die"].setdefault("pg", {})
pg["bumps"] = dict(pitch_um=150.0, pad_um=70.0, fields=[dict(
    name="a0_p75", pitch_um=75.0, pad_um=37.5, keep_um=75.0, rects_um=rects,
    note=f"OWNER 10-28 19:58 option (c): 75-um power bump field over the A0 array incl. streets = {len(a0)} A0 outlines "
         f"+{DIL:g} um (QC-PG-4 MEp75/MDp75 solve); rest of the die 150/70")])
for g in pg["grid"]:
    if g["layer"] == "M9": g["width_um"] = 0.672
P.setdefault("note", "")
Path(dst).write_text(json.dumps(P, indent=1) + "\n")
print(json.dumps(dict(a0=len(a0), rects=len(rects), field_mm2=round(area, 2), dil=DIL)))
