#!/usr/bin/env python3
"""S81 source-pin event (DIE-S81-28, 2026-10-29): dsdv_eng_rr_h0 clock ck = explicit M5 interior entry.

Fix-only plan pin delta on frozen plan_s13r2 (same form as the CFG7 event 28ba49f68).  The H0 kit
dsdv_eng_rr_h0_prefix48c_d25 consumed the d25 master-plan slice (METHODOLOGY 12.8a: centre clock entry, island ck_entry
M9->M5 at (82.08, 133.92)); master_slice.slice_placements snaps it onto the M5 track x = 0.012 + 0.048*1710 = 82.092 at
CLOCK_PIN_SIZE 0.048 x 0.48 (GEOM-21).  The routed view carries exactly that pin (abstract RECT 82.068 133.68 82.116
134.16), but the plan pin table still had the bottom-up W-face M4 pin (0.096, 133.932) -> PIN_AUDIT 644/645.
This moves the plan pin table + plan LEF ck PORT to the routed/slice entry; nothing else changes.
H0 is not an early die tap (plan clock.core_taps early = ve_m/vsw/vn_a/vn_b): the partition-local tree of the u_eng
parent reaches the pin from M6 over the core (core obs_max M5), so the die tree (ot_clk s81_g03c2) is unchanged.
plan_s13r2 / die_plan.json reference the core by path (pins_file / lef) -> plan sha unchanged.

usage: python3 delta_h0_ck_m5_1029.py
"""
import json
import re
from pathlib import Path

S81 = Path(__file__).resolve().parent
PINS = S81 / "inputs/core_pins/dsdv_eng_rr_h0.json"
LEF = S81 / "cores/eng/lef/dsdv_eng_rr_h0.lef"
W, H = 164.16, 267.84
OLD = ("M4", 0.096, 133.932)
NEW = ("M5", 82.092, 133.92)
PIN_W, PIN_L = 0.048, 0.48


def rect():
    _, x, y = NEW
    k = (x - 0.012) / 0.048
    assert abs(k - round(k)) < 1e-6, ("off M5 track", x)
    r = (x - PIN_W / 2, y - PIN_L / 2, x + PIN_W / 2, y + PIN_L / 2)
    assert 0 < r[0] and r[2] < W and 0 < r[1] and r[3] < H
    return r


def edit_pins():
    txt = PINS.read_text()
    old = '"name": "ck",\n"layer": "%s",\n"x": %g,\n"y": %g\n' % OLD
    assert txt.count(old) == 1, "ck entry not in the expected form"
    txt = txt.replace(old, '"name": "ck",\n"layer": "%s",\n"x": %g,\n"y": %g\n' % NEW)
    d = json.loads(txt)
    d["source"] += ("; S81 source-pin event DIE-S81-28 2026-10-29 (delta_h0_ck_m5_1029.py): ck M4 W face "
                    "(0.096,133.932) -> M5 interior slice entry (82.092,133.92) 0.048x0.48 = routed view")
    # keep the file's indent-0 form; only the ck entry and the source string change
    src_old = json.loads(PINS.read_text())["source"]
    txt = txt.replace(json.dumps(src_old)[1:-1], json.dumps(d["source"])[1:-1], 1)
    assert json.loads(txt) == d
    PINS.write_text(txt)


def edit_lef():
    txt = LEF.read_text()
    old = "  PIN ck\n    DIRECTION INPUT ;\n    USE CLOCK ;\n    PORT\n      LAYER M4 ;\n        RECT 0.000 133.920 0.192 133.944 ;\n    END\n  END ck\n"
    assert txt.count(old) == 1, "ck PORT not in the expected form"
    x0, y0, x1, y1 = rect()
    new = ("  PIN ck\n    DIRECTION INPUT ;\n    USE CLOCK ;\n    PORT\n      LAYER M5 ;\n"
           f"        RECT {x0:.3f} {y0:.3f} {x1:.3f} {y1:.3f} ;\n    END\n  END ck\n")
    LEF.write_text(txt.replace(old, new))


if __name__ == "__main__":
    edit_pins()
    edit_lef()
    print("dsdv_eng_rr_h0 ck", OLD, "->", NEW, "rect", tuple(round(v, 3) for v in rect()))
