#!/usr/bin/env python3
"""TILE-FILL audit core: per-master outline vs real content, nested whitespace, macro channels, pin bound,
per-die instance census and wasted mm2.  Inputs: archive_index.json (scan_archive.py) + die contracts on main."""
import json, math, re, sys, collections

import os as _os
WT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", ".."))
IDX = json.load(open(sys.argv[1]))
ROWS = {r["block"]: r for r in IDX["rows"] if r.get("w") and r.get("closed_at")}
for r in IDX["rows"]:
    if r.get("w") and r.get("closed_at"):
        ROWS.setdefault(r["element"], r)
LEF = IDX["lefidx"]
RAW = re.compile(r"^(ot_rom_|ot_sram_|ot_rf_|fakeram|ot_hbm3e_phy|ot_pdie_|ot_qkvd_ucie|ot_qfd_serdes|ot_hbm_host_phy)")
STD_UTIL = 0.50      # owner slot grants: <= 50 % std-cell utilisation
MACRO_PACK = 1.15    # raw macros in abutted rows with a 20-um channel every second row
CHILD_PACK = 1.10    # hard children re-placed with 20-um channels
FACE_NS, FACE_WE, FACE_ADD = 0.12, 0.16, 8.64   # S-NET station face rule (um/pin + um)
MIN_DEPTH = 12.96


def swap(orient):
    return orient in ("E", "W", "FE", "FW", "R90", "R270", "MXR90", "MYR90")


class Model:
    def __init__(self):
        self.m = {}     # name -> dict(w,h,std,children:[(name,count)],src,boxes)

    def add(self, name, **kw):
        d = self.m.setdefault(name, {"name": name, "children": [], "std": None, "src": None})
        for k, v in kw.items():
            if v is not None:
                d[k] = v
        return d

    def get(self, name):
        if name in self.m:
            return self.m[name]
        r = ROWS.get(name)
        if r:
            ch = collections.Counter(c[0] for c in r.get("children", []))
            d = self.add(name, w=r["w"], h=r["h"], std=r.get("std_area") or 0.0, src="closed view " + r["job"],
                         pins=r.get("pins"), job=r["job"], boxes=r.get("children", []))
            d["children"] = sorted(ch.items())
            return d
        if name in LEF:
            l = LEF[name]
            return self.add(name, w=l["w"], h=l["h"], std=0.0 if RAW.match(name) else None,
                            src=("raw macro LEF" if RAW.match(name) else "LEF only (no closed view)"), raw=bool(RAW.match(name)))
        return self.add(name, src="unknown")

    def area(self, name):
        d = self.get(name)
        return (d.get("w") or 0) * (d.get("h") or 0)

    def deep(self, name, seen=()):
        """(raw macro area, std area, unknown-content outline area) over the whole subtree."""
        d = self.get(name)
        if d.get("raw") or (RAW.match(name) and not d["children"]):
            return (self.area(name), 0.0, 0.0)
        if name in seen:
            return (0, 0, 0)
        mac, std, unk = 0.0, (d.get("std") or 0.0), 0.0
        if d.get("std") is None and not d["children"]:
            return (0.0, 0.0, self.area(name))
        for c, n in d["children"]:
            a, b, u = self.deep(c, seen + (name,))
            mac += a * n; std += b * n; unk += u * n
        return (mac, std, unk)

    def child_outline(self, name):
        d = self.get(name)
        return sum(self.area(c) * n for c, n in d["children"])

    def raw_children(self, name):
        d = self.get(name)
        return sum(self.area(c) * n for c, n in d["children"] if self.get(c).get("raw") or RAW.match(c))


M = Model()


def channels(d):
    """Minimum facing gap between hard children (um); count of < 20 um non-abutted channels."""
    boxes = []
    for master, x, y, o, inst in d.get("boxes") or []:
        l = M.get(master)
        w, h = l.get("w"), l.get("h")
        if not w:
            continue
        if swap(o):
            w, h = h, w
        boxes.append((x, y, x + w, y + h))
    if len(boxes) < 1:
        return None
    W, H = d["w"], d["h"]
    gaps = []
    for i in range(len(boxes)):
        a = boxes[i]
        for j in range(i + 1, len(boxes)):
            b = boxes[j]
            ox = min(a[2], b[2]) - max(a[0], b[0])
            oy = min(a[3], b[3]) - max(a[1], b[1])
            if oy > 0 and ox <= 0:
                gaps.append(-ox)
            elif ox > 0 and oy <= 0:
                gaps.append(-oy)
    edge = [min(b[0], b[1], W - b[2], H - b[3]) for b in boxes]
    nz = [g for g in gaps if g > 0.05]
    return {"n_children": len(boxes), "min_channel_um": round(min(nz), 3) if nz else None,
            "abutted_pairs": sum(1 for g in gaps if g <= 0.05),
            "channels_lt20": sum(1 for g in nz if g < 20.0), "channels": len(nz),
            "min_edge_um": round(min(edge), 3), "bbox_children": [round(min(b[0] for b in boxes), 2), round(min(b[1] for b in boxes), 2),
                                                                 round(max(b[2] for b in boxes), 2), round(max(b[3] for b in boxes), 2)]}


def pin_bound(d):
    p = d.get("pins") or {}
    n = {f: sum(v.values()) for f, v in p.items() if f in "NSEW"}
    wmin = max([FACE_NS * n.get(f, 0) + FACE_ADD for f in "NS" if n.get(f, 0) > 2] or [0])
    hmin = max([FACE_WE * n.get(f, 0) + FACE_ADD for f in "EW" if n.get(f, 0) > 2] or [0])
    return min(wmin, d["w"]), min(hmin, d["h"]), n


def analyse(name, outline=None, src_outline=None):
    d = M.get(name)
    w, h = (outline or (d.get("w"), d.get("h")))
    if not w:
        return None
    A = w * h
    mac, std, unk = M.deep(name)
    if d.get("std") is None and not d["children"]:
        mac, std, unk = 0.0, 0.0, A
    content = mac + std
    own_std = d.get("std")
    ch_out = M.child_outline(name)
    raw_ch = M.raw_children(name)
    hard_ch = ch_out - raw_ch
    own_ws = A - ch_out - (own_std or 0)
    # re-pack targets
    t_keep = hard_ch * CHILD_PACK + raw_ch * MACRO_PACK + (own_std or 0) / STD_UTIL + unk
    t_flat = mac * MACRO_PACK + std / STD_UTIL + unk
    wp, hp, npins = pin_bound(dict(d, w=w, h=h)) if d.get("pins") else (0, 0, {})
    def with_pins(t):
        if wp and hp:
            return max(t, wp * hp)
        if wp:
            return wp * max(t / wp, MIN_DEPTH)
        if hp:
            return hp * max(t / hp, MIN_DEPTH)
        return t
    keep = min(A, with_pins(t_keep)); flat = min(A, with_pins(t_flat))
    pin_area = (wp * max(hp, MIN_DEPTH) if wp else 0) or (hp * MIN_DEPTH if hp else 0)
    row = {"master": name, "outline_um": [round(w, 3), round(h, 3)], "outline_um2": round(A, 1),
           "outline_src": src_outline or d.get("src"), "view": d.get("job"),
           "content_um2": round(content, 1), "raw_macro_um2": round(mac, 1), "std_um2": round(std, 1),
           "unknown_content_um2": round(unk, 1), "own_std_um2": None if own_std is None else round(own_std, 1),
           "hard_children": [[c, n] for c, n in d["children"] if not (M.get(c).get("raw") or RAW.match(c))],
           "raw_children": [[c, n] for c, n in d["children"] if (M.get(c).get("raw") or RAW.match(c))],
           "child_outline_um2": round(ch_out, 1), "own_level_whitespace_um2": round(own_ws, 1),
           "fill_pct": round(100 * content / A, 1) if A and not unk else None,
           "fill_pct_known": round(100 * content / A, 1) if A else None,
           "pins_per_face": npins, "pin_bound_um": [round(wp, 2), round(hp, 2)],
           "repack_keep_children_um2": round(keep, 1), "repack_flat_um2": round(flat, 1),
           "recoverable_keep_um2": round(A - keep, 1), "recoverable_flat_um2": round(A - flat, 1)}
    ch = channels(dict(d, w=w, h=h)) if d.get("boxes") else None
    if ch:
        row["channels"] = ch
    # classification
    dims_pin = (wp >= 0.9 * w if wp else False) or (hp >= 0.9 * h if hp else False)
    waste = A - content
    if A <= 0 or unk > 0.5 * A:
        cls = None
    elif row["recoverable_keep_um2"] < 0.2 * A and row["recoverable_flat_um2"] < 0.3 * A:
        cls = "a" if not dims_pin else "b"
    elif dims_pin and (A - with_pins(0)) < 0.35 * A:
        cls = "b"
    elif dims_pin:
        cls = "b+c"
    else:
        cls = "c"
    row["class"] = cls
    row["pin_bound_dim"] = dims_pin
    return row
