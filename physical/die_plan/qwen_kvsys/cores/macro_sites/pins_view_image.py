#!/usr/bin/env python3
"""QK-CORES-11 10-27: mirrored-view island ft image for a KV core pin view (GEOM-REVIEW-37 fMX FAIL STRUCTURAL).

    python3 pins_view_image.py R0_VIEW.json MIRROR_VIEW.json OUT.json [--view MX|MY|R180]

The plan's mirrored pin view (e.g. cores/kv3_pv_pair_pins_fMX_r25.json, 'exact MX image of r25m') carries the 12.2a1
island ft ports ft_ck_i/o_<k> and island_ft rects UN-imaged (copied from the R0 view), so in the fMX kit the die ft
cells sit where the R0 SRAMs' images land.  This writes OUT = MIRROR_VIEW with every ft_ck_* pin and every island_ft
arc rect replaced by the exact image of the R0 view's ones about the outline (MX: y' = H - y, rect y0' = H - y1,
y1' = H - y0; MY likewise in x); every other pin and key is unchanged.  Fail-closed: the R0 and mirror views must
carry the same ft pin names / arcs, and every non-ft pin of the mirror view must be untouched.  Output goes to a run-dir
plan copy, never into the shared plan dir; the plan owner takes the result as a plan delta (plan follows).
"""
import argparse
import copy
import json
import re
from pathlib import Path

FT = re.compile(r"ft_ck_[io]_\d+\Z")


def outline(doc):
    m = re.search(r"outline ([\d.]+) x ([\d.]+)", doc.get("frame", ""))
    if not m:
        raise SystemExit(f"pin view frame {doc.get('frame')!r}: no 'outline W x H'")
    return float(m.group(1)), float(m.group(2))


def image(r0, mir, view="MX"):
    if view not in ("MX", "MY", "R180"):
        raise SystemExit(f"view {view}: MX/MY/R180 only")
    w, h = outline(r0)
    if outline(mir) != (w, h):
        raise SystemExit(f"outline differs: R0 {w}x{h} vs mirror {outline(mir)}")
    fx, fy = view in ("MY", "R180"), view in ("MX", "R180")
    r0ft = {p["name"]: p for p in r0["pins"] if FT.fullmatch(p["name"])}
    mft = {p["name"] for p in mir["pins"] if FT.fullmatch(p["name"])}
    if set(r0ft) != mft or not mft:
        raise SystemExit(f"ft pins differ: R0 {sorted(r0ft)} vs mirror {sorted(mft)}")
    out = copy.deepcopy(mir)
    for p in out["pins"]:
        if p["name"] in r0ft:
            q = r0ft[p["name"]]
            p["x"] = round(w - q["x"], 4) if fx else q["x"]
            p["y"] = round(h - q["y"], 4) if fy else q["y"]
    ra = {a["source"]: a for a in (r0.get("island_ft") or {}).get("arcs", [])}
    ma = (out.get("island_ft") or {}).get("arcs", [])
    if {a["source"] for a in ma} != set(ra) or not ma:
        raise SystemExit("island_ft arcs differ between R0 and mirror views")
    for a in ma:
        x0, y0, x1, y1 = ra[a["source"]]["rect_um"]
        if fx:
            x0, x1 = round(w - x1, 4), round(w - x0, 4)
        if fy:
            y0, y1 = round(h - y1, 4), round(h - y0, 4)
        a["rect_um"] = [x0, y0, x1, y1]
    for a, b in zip(mir["pins"], out["pins"]):
        if a["name"] != b["name"] or (not FT.fullmatch(a["name"]) and a != b):
            raise SystemExit(f"non-ft pin changed: {a['name']}")
    note = (f"QK-CORES-11 10-27: island ft ports + island_ft rects = exact {view} image of the R0 view "
            f"(were copied un-imaged; GEOM-REVIEW-37)")
    out["source"] = f"{out.get('source', '')} | {note}"
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("r0"); ap.add_argument("mirror"); ap.add_argument("out")
    ap.add_argument("--view", default="MX")
    a = ap.parse_args()
    o = image(json.load(open(a.r0)), json.load(open(a.mirror)), a.view)
    Path(a.out).write_text(json.dumps(o, indent=1) + "\n")
    print(json.dumps({p["name"]: [p["x"], p["y"]] for p in o["pins"] if FT.fullmatch(p["name"])}),
          json.dumps([a["rect_um"] for a in o["island_ft"]["arcs"]]))
