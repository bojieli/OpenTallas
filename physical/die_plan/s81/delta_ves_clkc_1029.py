#!/usr/bin/env python3
"""S81 source-pin event (DIE-S81-32, 2026-10-29): ot_s81sl_ve_s clk = explicit M5 interior centre entry (face C).

Fix-only plan pin delta on frozen plan_s13r2, same form as the H0 event 330ee0e6e50 (delta_h0_ck_m5_1029.py).
The ve_s kits consume the master-plan slice (METHODOLOGY 12.8a centre clock entry: island ck_entry rect
[79.92,170.64,84.24,174.96], via stack M9->M5, clock_pin M5 (82.08,172.8)); master_slice snaps it onto the M5 track
x = 0.012 + 0.048*1710 = 82.092 at CLOCK_PIN_SIZE 0.048 x 0.48.  The routed ce27m view carries exactly that pin
(abstract RECT 82.068 172.56 82.116 173.04) but the plan pin table still had the E-face pin (164.124,172.332)
-> PIN_AUDIT 487/488 (DIE-S81-30 19:02).  This moves the plan pin table + plan LEF clk PORT to the slice entry and
opens the plan LEF M6/M7 OBS over the ck_entry island so the parent can drop onto the M5 pin (the plan LEF reserves
M6/M7 for the core, obs_max M7; the routed abstract obstructs to M5 only).  Nothing else changes.
ve_s is not an early die tap (plan clock.core_taps early = ve_m/vsw/vn_a/vn_b; no u_ve.u_s tap rows): the leaf
partition-local tree reaches the pin, so the die tree (ot_clk s81_g03c2) is unchanged.  plan_s13r2 / die_plan.json
reference the core by path (pins_file / lef) -> plan sha unchanged.  Mirrored instances (MY/R180) use the same
template table; x 82.092 mirrors to 82.068 (+track offset 0.024 = on track), as every other template pin.

usage: python3 delta_ves_clkc_1029.py   (asserts exact old forms; a second run refuses)
"""
import hashlib
import json
from pathlib import Path

S81 = Path(__file__).resolve().parent
PINS = S81 / "inputs/core_pins/ot_s81sl_ve_s_tpl.json"
LEF = S81 / "cores/leaf/lef/ot_s81sl_ve_s_tpl.lef"
W, H = 164.16, 345.6
OLD = ("M5", 164.124, 172.332)
NEW = ("M5", 82.092, 172.8)
PIN_W, PIN_L = 0.048, 0.48
ISLAND = (79.92, 170.64, 84.24, 174.96)  # slice islands[ck_entry].rect_um


def rect():
    _, x, y = NEW
    k = (x - 0.012) / 0.048
    assert abs(k - round(k)) < 1e-6, ("off M5 track", x)
    r = (x - PIN_W / 2, y - PIN_L / 2, x + PIN_W / 2, y + PIN_L / 2)
    assert ISLAND[0] < r[0] and r[2] < ISLAND[2] and ISLAND[1] < r[1] and r[3] < ISLAND[3]
    return r


def edit_pins():
    txt = PINS.read_text()
    old = '"name": "clk",\n"layer": "%s",\n"x": %g,\n"y": %g\n' % OLD
    assert txt.count(old) == 1, "clk entry not in the expected form"
    d0 = json.loads(txt)
    txt = txt.replace(old, '"name": "clk",\n"layer": "%s",\n"x": %g,\n"y": %g\n' % NEW)
    d = json.loads(txt)
    d["source"] += ("; S81 source-pin event DIE-S81-32 2026-10-29 (delta_ves_clkc_1029.py): clk M5 E face "
                    "(164.124,172.332) -> M5 interior slice entry (82.092,172.8) 0.048x0.48 = routed ce27m view; "
                    "plan LEF M6/M7 OBS opened over island ck_entry")
    d["pinhash"] = hashlib.sha256(json.dumps(d["pins"], sort_keys=True).encode()).hexdigest()[:12]
    txt = txt.replace(json.dumps(d0["source"])[1:-1], json.dumps(d["source"])[1:-1], 1)
    txt = txt.replace('"pinhash": "%s"' % d0["pinhash"], '"pinhash": "%s"' % d["pinhash"], 1)
    assert json.loads(txt) == d
    PINS.write_text(txt)
    return d0["pinhash"], d["pinhash"]


def edit_lef():
    txt = LEF.read_text()
    old = ("  PIN clk\n    DIRECTION INPUT ;\n    USE SIGNAL ;\n    PORT\n      LAYER M5 ;\n"
           "        RECT 164.0880 172.0920 164.1600 172.5720 ;\n    END\n  END clk\n")
    assert txt.count(old) == 1, "clk PORT not in the expected form"
    x0, y0, x1, y1 = rect()
    new = ("  PIN clk\n    DIRECTION INPUT ;\n    USE SIGNAL ;\n    PORT\n      LAYER M5 ;\n"
           f"        RECT {x0:.4f} {y0:.4f} {x1:.4f} {y1:.4f} ;\n    END\n  END clk\n")
    txt = txt.replace(old, new)
    a, b, c, e = ISLAND
    for lay in ("M6", "M7"):
        o = f"    LAYER {lay} ;\n      RECT 0 0 164.160 345.600 ;\n"
        assert txt.count(o) == 1, (lay, "OBS not in the expected full-outline form")
        n = (f"    LAYER {lay} ;\n      RECT 0 0 164.160 {b:.3f} ;\n      RECT 0 {e:.3f} 164.160 345.600 ;\n"
             f"      RECT 0 {b:.3f} {a:.3f} {e:.3f} ;\n      RECT {c:.3f} {b:.3f} 164.160 {e:.3f} ;\n")
        txt = txt.replace(o, n)
    LEF.write_text(txt)


if __name__ == "__main__":
    h = edit_pins()
    edit_lef()
    print("ot_s81sl_ve_s clk", OLD, "->", NEW, "rect", tuple(round(v, 4) for v in rect()), "pinhash", h)
