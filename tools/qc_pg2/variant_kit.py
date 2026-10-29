#!/usr/bin/env python3
"""QC-PG-2 (10-27): derive PDNSim window-kit variants from a QC-PG-MAP kit (same grid/window), linear class solves.
  --load-rect x0,y0,x1,y1 --load-w W     replace ALL set_pdnsim_inst_power lines by W spread uniformly over the rect
                                          (window-local um, split over 43.07-um load blocks by overlap area)
  --scale F                               multiply every existing load by F
  --field x0,y0,x1,y1 --b75 KIT75         local 75-um bump field: 150-um bumps (70 pad) outside the rect, the 75-um kit's
                                          bumps (37.5 pad) inside it (bump centre test), per-bump pad size
usage: variant_kit.py BASEKIT OUTKIT [opts]"""
import argparse, re, shutil
from pathlib import Path
ap = argparse.ArgumentParser(); ap.add_argument("base"); ap.add_argument("out")
ap.add_argument("--load-rect"); ap.add_argument("--load-w", type=float); ap.add_argument("--scale", type=float)
ap.add_argument("--field", action="append", default=[]); ap.add_argument("--b75"); ap.add_argument("--keep150", action="store_true", help="keep every 150-um bump, add only the 75-um bumps >= 37.5 um from a kept bump (superset field)")
a = ap.parse_args()
B, O = Path(a.base), Path(a.out)
if O.exists(): shutil.rmtree(O)
shutil.copytree(B, O, ignore=shutil.ignore_patterns("ir_*.csv", "psm.log", "psm_*.rpt"))
for f in ("psm.image.txt", "run.log"): (O / f).unlink(missing_ok=True)
t = (O / "psm/psm.tcl").read_text()
if a.load_rect or a.scale:
    lines = [l for l in t.split("\n") if not l.startswith("set_pdnsim_inst_power")]
    i = next(k for k, l in enumerate(t.split("\n")) if l.startswith("set_pdnsim_inst_power"))
    if a.scale:
        new = []
        for m in re.finditer(r"^set_pdnsim_inst_power -inst (\S+) -power (\S+)", t, re.M):
            new.append(f"set_pdnsim_inst_power -inst {m[1]} -power {float(m[2]) * a.scale:.8f}")
    else:
        x0, y0, x1, y1 = map(float, a.load_rect.split(","))
        sz = float(re.search(r"SIZE (\S+) BY", (O / "psm/irblk.lef").read_text())[1])
        pl = {m[1]: (float(m[2]), float(m[3])) for m in re.finditer(r"^ot_pl (\S+) (\S+) (\S+)", t, re.M)}
        A = (x1 - x0) * (y1 - y0); new = []; tot = 0
        for k, (bx, by) in pl.items():
            ov = max(0, min(x1, bx + sz) - max(x0, bx)) * max(0, min(y1, by + sz) - max(y0, by))
            if ov > 0:
                p = a.load_w * ov / A; tot += p; new.append(f"set_pdnsim_inst_power -inst {k} -power {p:.8f}")
        assert abs(tot - a.load_w) < 1e-6 * max(1, a.load_w), tot
    lines[i:i] = new; t = "\n".join(lines)
    (O / "psm/psm.tcl").write_text(t)
if a.field:
    rects = [list(map(float, f.split(","))) for f in a.field]
    inside = lambda x, y: any(r[0] <= x <= r[2] and r[1] <= y <= r[3] for r in rects)
    bt = (O / "psm/bumps.tcl").read_text().split("\n")
    b75 = [l for l in (Path(a.b75) / "psm/bumps.tcl").read_text().split("\n") if l.startswith("ot_pad ")]
    head = [l for l in bt if not l.startswith("ot_pad ") and not l.startswith('puts "OT_BUMPS')]
    head = [l.replace("proc ot_pad {net k bx by} {", "proc ot_pad {net k bx by {pad 70}} {").replace(
        "global block m9 bump_dbu bump_shapes pad_pins pad_fallback pad_area pad_half",
        "global block m9 bump_dbu bump_shapes pad_pins pad_fallback pad_area\n  set pad_half [expr {round($pad*$bump_dbu/2.0)}]") for l in head]
    assert any("{pad 70}" in l for l in head)
    pads = []; n150 = n75 = 0
    for l in bt:
        if l.startswith("ot_pad "):
            _, net, k, x, y = l.split()
            if a.keep150 or not inside(float(x), float(y)): pads.append((net, x, y, 70)); n150 += 1
    for l in b75:
        _, net, k, x, y = l.split()
        if inside(float(x), float(y)):
            if a.keep150 and any(abs(float(x) - float(q[1])) < 37.5 and abs(float(y) - float(q[2])) < 37.5 for q in pads if q[3] == 70): continue
            pads.append((net, x, y, 37.5)); n75 += 1
    body = [f"ot_pad {net} {k} {x} {y} {p}" for k, (net, x, y, p) in enumerate(pads)]
    body.append(f'puts "OT_BUMPS mixed b150 {n150} b75 {n75} pad_pins $pad_pins pad_fallback $pad_fallback m9_contact_um2 [format %.1f $pad_area]"')
    (O / "psm/bumps.tcl").write_text("\n".join(head + body) + "\n")
    print("bumps 150:", n150, "75:", n75)
print("kit", O)
