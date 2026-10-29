#!/usr/bin/env python3
"""S81-028 part 2 (DIE-S81-24, 2026-10-29, COORD follow-up): GEOM-21 clock entry for the 5 more leaf cores that block
the ot_s81sl_leaf kits (CORES-EARLY-11): ot_s81sl_ve_m, ve_s, vn_a, vn_b, vsw.  Sibling of delta_clkpin_m5_1029.py
(rxsf / vs); same rule: the clock pin becomes an M5 EDGE rectangle >= 0.048 x 0.48 um whose centre is on the kit M5
track (x = 0.012 + 0.048 k, the convention of every template M5 pin), touching its face; same face, nearest legal
site; nothing else moves.

  ve_m  S face M5 x 86.316 (on track): 0.024x0.084 -> 0.048x0.48, centre y 0.042 -> 0.24.
  ve_s  E face M4 (164.118, 172.332) -> M5 0.072x0.48 centre (164.124, 172.332): on a 164.16-um outline no 0.048-wide
        rect touching the E face is centred on a track; 0.072 wide is the narrowest that is (track 3419).
  vn_a  W face M4 (0.042, 81.9)   -> M5 0.120x0.48 centre (0.06, 81.9): narrowest W-edge rect centred on track 1.
  vn_b  W face M4 (0.042, 86.316) -> M5 0.120x0.48 centre (0.06, 86.316).
  vsw   S face M3 0.018x0.038 (56.673, 0.019) -> M5 0.048x0.48 centre (56.652, 0.24) (nearest track 1180; no M5 shape
        within 0.06 um, CHECKED).  The closed view LEF physical/ref_tile/s81sl_vsw/views/... is NOT edited: the plan pin
        contract moves to a plan-owned copy cores/leaf/lef/ot_s81sl_vsw.lef (only the clk PORT differs) and the plan
        hard_cores rows of ot_s81sl_vsw are repointed (--plans-only works on any plan form, e.g. plan_s13r2).
The 4 template LEFs (cores/leaf/lef/*_tpl.lef, plan-owned stubs) are edited in place.

usage: python3 delta_clkpin_m5_1029b.py [--plan PLAN.json ...] [--plans-only]   (default plan: die_plan.json)
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

S81 = Path(__file__).resolve().parent
REPO = S81.parents[2]
LEAF = "physical/die_plan/s81/cores/leaf/lef/"
VSW_REF = "physical/ref_tile/s81sl_vsw/views/ot_s81sl_vsw/ot_s81sl_vsw.lef"
# module: pins table, old (layer, x, y), new (x, y), rect (x0, y0, x1, y1), lef source, lef target
EDITS = {
    "ot_s81sl_ve_m": ("inputs/core_pins/ot_s81sl_ve_m_tpl.json", ("M5", 86.316, 0.042), (86.316, 0.24),
                      (86.292, 0.0, 86.340, 0.48), LEAF + "ot_s81sl_ve_m_tpl.lef", LEAF + "ot_s81sl_ve_m_tpl.lef"),
    "ot_s81sl_ve_s": ("inputs/core_pins/ot_s81sl_ve_s_tpl.json", ("M4", 164.118, 172.332), (164.124, 172.332),
                      (164.088, 172.092, 164.160, 172.572), LEAF + "ot_s81sl_ve_s_tpl.lef", LEAF + "ot_s81sl_ve_s_tpl.lef"),
    "ot_s81sl_vn_a": ("inputs/core_pins/ot_s81sl_vn_a_tpl.json", ("M4", 0.042, 81.9), (0.06, 81.9),
                      (0.0, 81.66, 0.12, 82.14), LEAF + "ot_s81sl_vn_a_tpl.lef", LEAF + "ot_s81sl_vn_a_tpl.lef"),
    "ot_s81sl_vn_b": ("inputs/core_pins/ot_s81sl_vn_b_tpl.json", ("M4", 0.042, 86.316), (0.06, 86.316),
                      (0.0, 86.076, 0.12, 86.556), LEAF + "ot_s81sl_vn_b_tpl.lef", LEAF + "ot_s81sl_vn_b_tpl.lef"),
    "ot_s81sl_vsw": ("inputs/core_pins/ot_s81sl_vsw.json", ("M3", 56.673, 0.019), (56.652, 0.24),
                     (56.628, 0.0, 56.676, 0.48), VSW_REF, LEAF + "ot_s81sl_vsw.lef"),
}
PIN = "clk"


def pinhash(pins):
    return hashlib.sha256(json.dumps(pins, sort_keys=True).encode()).hexdigest()[:12]


def check_rect(new, r, W, H):
    x, y = new
    x0, y0, x1, y1 = r
    assert abs((x0 + x1) / 2 - x) < 1e-6 and abs((y0 + y1) / 2 - y) < 1e-6, ("rect not centred", new, r)
    assert x1 - x0 >= 0.048 - 1e-9 and y1 - y0 >= 0.48 - 1e-9, ("rect < 0.048x0.48", r)
    k = (x - 0.012) / 0.048
    assert abs(k - round(k)) < 1e-6, ("centre off M5 track", x)
    assert min(x0, y0, W - x1, H - y1) < 1e-6 and min(x0, y0) >= 0 and x1 <= W + 1e-9 and y1 <= H + 1e-9, \
        ("rect must touch its face and stay inside", r)


def edit(mod, e):
    pins_f, old, new, r, lsrc, ldst = e
    txt = (REPO / lsrc).read_text()
    W, H = map(float, re.search(r"SIZE ([\d.]+) BY ([\d.]+)", txt).groups()) if "SIZE" in txt else (None, None)
    f = S81 / pins_f
    d = json.loads(f.read_text())
    if W is None:  # template stub LEFs carry no SIZE: outline from the full-outline M5 OBS
        m = re.search(r"OBS.*?LAYER M5 ;\s*RECT\s+0(?:\.0+)?\s+0(?:\.0+)?\s+([\d.]+)\s+([\d.]+)", txt, re.S)
        W, H = float(m.group(1)), float(m.group(2))
    check_rect(new, r, W, H)
    pat = re.compile(r"(  PIN %s\n(?:(?!  END %s\n).)*?    PORT\n)(.*?)(    END\n  END %s\n)" % ((PIN,) * 3), re.S)
    m = pat.search(txt)
    assert m and len(pat.findall(txt)) == 1, mod
    port = f"      LAYER M5 ;\n        RECT {r[0]:.4f} {r[1]:.4f} {r[2]:.4f} {r[3]:.4f} ;\n"
    (REPO / ldst).write_text(txt[:m.start(2)] + port + txt[m.end(2):])
    # vsw still carries the CORE-KS LEF-rect pinhash (core_pins_gen.py); every later S81 pin delta re-hashes with the
    # json form below (delta_bfcfg47 / delta_hcplpins / pin_template), so that is what is written.
    q = [p for p in d["pins"] if p["name"] == PIN]
    assert len(q) == 1 and (q[0]["layer"], q[0]["x"], q[0]["y"]) == old, (mod, q)
    q[0].update(layer="M5", x=new[0], y=new[1])
    d["lef"] = ldst
    d["pinhash"] = pinhash(d["pins"])
    d["source"] = d.get("source", "") + (
        f"; S81-028 DIE-S81-24 2026-10-29 (delta_clkpin_m5_1029b.py): clock {PIN} {old[0]}({old[1]},{old[2]}) -> "
        f"M5({new[0]},{new[1]}) {r[2]-r[0]:.3f}x{r[3]-r[1]:.3f} edge rectangle on the M5 track (GEOM-21)")
    end_nl = f.read_text().endswith("\n")
    f.write_text(json.dumps(d, indent=0) + ("\n" if end_nl else ""))
    return W, H


def edit_plan(path):
    txt = Path(path).read_text()
    old = f'"module":"ot_s81sl_vsw","lef":"{VSW_REF}"'
    new_lef = EDITS["ot_s81sl_vsw"][5]
    n = txt.count(old)
    if n:   # compact one-row-per-core form (main die_plan.json): textual swap keeps every other byte
        Path(path).write_text(txt.replace(old, f'"module":"ot_s81sl_vsw","lef":"{new_lef}"'))
        return n
    p = json.loads(txt)
    for t in p["partition_types"].values():
        for h in t.get("hard_cores", []):
            if h["module"] == "ot_s81sl_vsw" and h.get("pins_file") == EDITS["ot_s81sl_vsw"][0]:
                assert h["lef"] == VSW_REF, h["lef"]
                h["lef"] = new_lef
                n += 1
    Path(path).write_text(json.dumps(p, indent=1) + "\n")
    return n


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="append")
    ap.add_argument("--plans-only", action="store_true")
    a = ap.parse_args()
    if not a.plans_only:
        for mod, e in EDITS.items():
            W, H = edit(mod, e)
            print(mod, e[1], "->", ("M5",) + e[2], "rect", e[3], "outline", (W, H))
    for pl in a.plan or [str(S81 / "die_plan.json")]:
        print(pl, "vsw hard_cores lef ->", EDITS["ot_s81sl_vsw"][5], edit_plan(pl))
