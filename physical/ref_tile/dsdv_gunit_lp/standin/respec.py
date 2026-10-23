#!/usr/bin/env python3
"""GUNIT3 re-kit of dsdv_gunit_lp: L5 n32 (388.8x302.4) + L1f 2x2 (A 259.2x302.4 -> lp, B 302.4x345.6 -> lp_b)."""
import json, sys, copy
from pathlib import Path
wt = Path(sys.argv[1])
src = wt / "tools/ref_tile/specs_pl_gunit/dsdv_gunit_lp.json"
base = json.loads(src.read_text())
def at(inst):
    return next(c for c in base["children"] if c["inst"] == inst)
def make(name, fw, fh, standin_l1f):
    s = copy.deepcopy(base)
    s["name"] = name
    pos = {}
    # col A unchanged (L5 n32 is 388.8 wide: right edge 432)
    xb = 432.0; xc = xb + fw + 43.2
    y0, y1 = 43.2, 43.2 + fh + 43.2
    pos["*u_l1f0"] = (xb, y0); pos["*u_l1f1"] = (xb, y1)
    pos["*u_l1f3"] = (xc, y0); pos["*u_l1f2"] = (xc, y1)
    yend = y1 + fh                      # bottom of the 2x2 L1f block
    # L1c (fo_* hub of the 4 fronts) under the 2x2, centred on the B|C gap, on the lattice
    pos["*u_l1c"] = (xc - 43.2, yend + 43.2)
    # hc right column: right of L5 (x >= 475.2)
    pos["*u_l0r"] = (475.2, 820.8); pos["*u_l4r"] = (475.2, 1036.8); pos["*u_l5f"] = (475.2, 1209.6)
    for c in s["children"]:
        if c["inst"] in pos:
            c["at"] = [round(v, 4) for v in pos[c["inst"]]]
        if c["inst"].startswith("*u_l1f"):
            c["view"] = standin_l1f
    w = round(xc + fw + 43.2, 4)
    # L5 n32 N face: vo_n at child x 16-234, vi_n at 44-273 (parent +43.2): vo_n left, vi_n right (was reversed)
    s["pin_ranges"]["vo_n"] = [43.2, 194.4]; s["pin_ranges"]["vi_n"] = [194.4, 345.6]
    s["outline"] = {"w": w, "h": base["outline"]["h"], "exact": True}
    s.setdefault("job", {})
    s["job"]["tag"] = "lp3" if name == "dsdv_gunit_lp" else "lp3b"
    s["job"]["purpose"] = (f"S81 dsdv_gunit landed-region parent, GUNIT3 re-kit: L5 n32 388.8x302.4 stand-in, L1f {fw}x{fh} "
                           f"stand-in 2x2, outline {w}x{s['outline']['h']} (diagnostic)")
    s["structural_change"] = base["structural_change"] + (f" | GUNIT3 10-20: re-kit for L5 n32 (388.8 wide) and L1f {fw}x{fh} "
        f"(2x2 fronts, L1c hub under the B|C gap, hc L0r/L4r/L5f at x 475.2); outline {w} x 1468.8")
    return s, w
for name, fw, fh, sv in [("dsdv_gunit_lp", 259.2, 302.4, "physical/ref_tile/dsdv_gunit_lp/standin/dsdv_gunit_l1f"),
                         ("dsdv_gunit_lp_b", 302.4, 345.6, "physical/ref_tile/dsdv_gunit_lp_b/standin/dsdv_gunit_l1f")]:
    s, w = make(name, fw, fh, sv)
    out = wt / f"tools/ref_tile/specs_pl_gunit/{name}.json"
    out.write_text(json.dumps(s, indent=1) + "\n")
    print(name, w, [(c["inst"], c["at"]) for c in s["children"]])
