#!/usr/bin/env python3
"""S81-ELEM2-GUNIT 10-21: dsdv_gunit_lp re-kit for the CURRENT main sources (dsdv_gunit.sv 24b63569 + every child at its
main blob): L5 = CLOSED exact view dsdv_gunit_l5-g3-37cf95cf2 (345.6x302.4, blob b21f0a4c), L1f = FBd 388.8x345.6
(stand-in from its --cts gate until job dsdv_gunit_l1f_d-n32-bb930dd44 closes; then pass --l1f-view).
MAIN lp  : fronts 2x2 at x 432 / 864 (43.2 channel), L1c E of col C at (1296, 216), outline 1425.6 x 1468.8.
FALLBACK lp_b: same RTL, 86.4 channels (col C x 907.2, L1c x 1339.2) -> outline 1468.8 x 1468.8 (routing relief).
usage: respec_lp4.py WT [--l1f-view PATH]"""
import json, sys, copy
from pathlib import Path
wt = Path(sys.argv[1])
l1f_view = sys.argv[sys.argv.index("--l1f-view") + 1] if "--l1f-view" in sys.argv else \
    "physical/ref_tile/dsdv_gunit_lp/standin/dsdv_gunit_l1f"
diag = "--l1f-view" not in sys.argv
base = json.loads((wt / "tools/ref_tile/specs_pl_gunit/dsdv_gunit_lp_b.json").read_text())
FW = 388.8
def make(name, chan):
    s = copy.deepcopy(base)
    s["name"] = name
    xb = 432.0; xc = round(xb + FW + chan, 4); xl1c = round(xc + FW + 43.2, 4)
    pos = {"*u_l3": (43.2, 43.2), "*u_l1": (43.2, 259.2), "*u_l2": (43.2, 518.4), "*u_l0": (43.2, 777.6),
           "*u_l4": (43.2, 993.6), "*u_l5": (43.2, 1123.2),
           "*u_l1f0": (xb, 43.2), "*u_l1f1": (xb, 432.0), "*u_l1f3": (xc, 43.2), "*u_l1f2": (xc, 432.0),
           "*u_l1c": (xl1c, 216.0),
           "*u_l0r": (432.0, 820.8), "*u_l4r": (432.0, 1036.8), "*u_l5f": (432.0, 1209.6)}
    for c in s["children"]:
        c["at"] = list(pos[c["inst"]])
        if c["inst"].startswith("*u_l1f"):
            c["view"] = l1f_view
        if c["inst"] == "*u_l5":
            c["view"] = "physical/ref_tile/dsdv_gunit_l5/views/dsdv_gunit_l5"
    w = round(xl1c + 86.4 + 43.2, 4)
    s["outline"] = {"w": w, "h": 1468.8, "exact": True}
    # L5 g3 N face: vi_n child x 0.9-76, vo_n 37.8-108 -> parent x 44-151; cw / sid / fault move to the W face over the
    # L1|L2 gap channel (L2 has them on its E face; the E face of this outline is 1000+ um away behind the fronts)
    s["pins"]["E"] = []
    s["pins"]["W"] = ["ck_hc", "rst_n", "cw_v", "cw_a", "cw_d", "sid", "fault"]
    s["pin_ranges"].update({"vi_n": [43.2, 151.2], "vo_n": [151.2, 259.2],
                            "cw_v": [432.0, 433.0], "cw_a": [434.0, 444.0], "cw_d": [446.0, 590.0],
                            "sid": [592.0, 596.0], "fault": [598.0, 599.0]})
    s["diagnostic"] = diag
    # 276-b rungs / 256-b cw_d on ranged faces need a defined bit order (gate pin_order); L1f precedent ea03a00de
    s["route"]["pin_balance"] = {"group_max": 1, "h": "M4", "v": "M5"}
    s["route"]["peak_ram_gb"] = 300   # 10-18 lp gates died in GRT at 64 / 160 GB
    s["reset_landing"] = {"enable": False, "reason": "the RTL lands it: tools/landed_parent/lp.py regional reset runs (rst_n -> per-region registered run, depth 4, lpr_c_<inst> per child; record results/arch/landed_parent_1018/gunit/dsdv_gunit_lp_record.json)"}
    j = s.setdefault("job", {})
    j["owner"] = "Claude:S81-ELEM2-GUNIT"; j["branch"] = "claude/s81-gunit-lp4-1021"
    j["tag"] = "lp4" if name == "dsdv_gunit_lp" else "lp4b"
    j["purpose"] = (f"S81 dsdv_gunit landed-region parent on CURRENT main child sources (L5 g3 view, L1f FBd 388.8x345.6 "
                    f"{'stand-in' if diag else 'view'}), outline {w}x1468.8, channel {chan}")
    j["submit"] = not diag
    j["hold_merge"] = "diagnostic: L1f stand-in abstract; real gate after its closed view" if diag else ""
    s["structural_change"] = base["structural_change"].split(" | GUNIT3")[0] + (
        f" | S81-ELEM2-GUNIT 10-21: re-kit on current main child views (L0/L0r/L1/L1c/L2(refinalized)/L3/L4/L4r/L5(g3)/L5f "
        f"CLOSED, exact blobs) + L1f FBd 388.8x345.6 x4: fronts 2x2 x {xb}/{xc} ({chan} channel), L1c E of col C "
        f"(x {xl1c}, y 216 centred on the front rows), hc side leaves at x 432; cw/sid/fault on the W face over the L1|L2 "
        f"gap; outline {w} x 1468.8")
    out = wt / f"tools/ref_tile/specs_pl_gunit/{name}.json"
    out.write_text(json.dumps(s, indent=1) + "\n")
    print(name, w, [(c["inst"], c["at"]) for c in s["children"]])
make("dsdv_gunit_lp", 43.2)
make("dsdv_gunit_lp_b", 86.4)
