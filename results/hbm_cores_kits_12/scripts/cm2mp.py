#!/usr/bin/env python3
"""HBM-CORES-KITS-12: plan core_macros.json KNOWN rects -> opentallas.macro_placement.v1 JSON (+ .est.json sizes/halo for
mk_c20 --avoid-macros).  origin = rect lower-left; master from the entry, else the unique LEF whose SIZE matches the rect."""
import json, sys, glob, re
from pathlib import Path
cm, wt, mod, out = sys.argv[1:5]
d = json.load(open(cm)); e = d["cores"][mod]; halo = float(d.get("halo_um", 4.32))
lefs = {}
for f in glob.glob(f"{wt}/physical/asap7_memory_macros*/*/*.lef"):
    m = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", open(f).read())
    if m: lefs[Path(f).stem] = (float(m.group(1)), float(m.group(2)))
mp, masters = [], {}
for q in e["macros"]:
    x0, y0, x1, y1 = q["rect_um"]; w, h = x1 - x0, y1 - y0
    ms = q.get("master")
    if not ms:
        c = [k for k, (a, b) in lefs.items() if abs(a - w) < 0.01 and abs(b - h) < 0.01]
        c = [k for k in c if k.endswith("r2c2")] if len(c) > 1 else c
        if len(c) != 1: raise SystemExit(f"{mod} {q['name']}: master ambiguous {c} for {w:.3f}x{h:.3f}")
        ms = c[0]
    masters[ms] = dict(w=lefs[ms][0], h=lefs[ms][1])
    mp.append(dict(k=q["name"][len("u_fcore."):] if q["name"].startswith("u_fcore.") else q["name"], macro=ms, origin_um=[round(x0, 3), round(y0, 3)], orient=q.get("orient", "R0")))
json.dump(dict(schema="opentallas.macro_placement.v1", design=mod, outline_um=e.get("outline_um"), macro_placement=mp,
               note=f"from plan core_macros.json status {e['status']} basis {e.get('basis')}"), open(out, "w"), indent=1)
json.dump(dict(halo_um=halo, masters=masters), open(out[:-5] + ".est.json", "w"), indent=1)
print(mod, len(mp), "macros", sorted(masters))
