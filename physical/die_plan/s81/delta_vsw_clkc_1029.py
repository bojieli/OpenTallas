#!/usr/bin/env python3
"""S81 source-pin event (DIE-S81-32, 2026-10-29; COORD 20:4x approved ASK default (b)): ot_s81sl_vsw clk = explicit M5
interior centre entry (face C) + the 74 early die-tap rows moved onto it.

Fix-only plan delta on frozen plan_s13r2 (H0 330ee0e6e50 / ve_s 541266add0c form, plus the early-tap datum move).
The approved VSW in-core clock plan (Codex vsw_replan slice, sha256 6a022fe2...) has island ck_entry
[105.30,115.02,109.62,119.34], via stack M9->M5, clock_pin M5 (107.46,117.18); master_slice snaps it onto the M5
track x = 0.012 + 0.048*2239 = 107.484 at CLOCK_PIN_SIZE 0.048 x 0.48 -> every VSW kit places clk there, while the
plan pin table/LEF kept the S-face pin (56.652,0.24) -> PIN_AUDIT would fail 1 pin and the die tree would land on
the S face while the core tree starts at the centre.
Changes (nothing else):
  inputs/core_pins/ot_s81sl_vsw_tpl.json  clk (56.652,0.24) -> (107.484,117.18), pinhash recomputed
  cores/leaf/lef/ot_s81sl_vsw_tpl.lef     clk PORT M5 RECT -> 107.460 116.940 107.508 117.420 (USE SIGNAL kept);
                                          plan LEF obstructs M1-M5 only (obs_max M5): the parent drops from M6, no OBS edit
  plan_s13r2.json clock.taps[] kind core 'u_lf.u_vsw.clk' (74 rows: 33 R0, 41 MX): xy += orient(dx, dy) with
  (dx, dy) = new - old pin = (50.832, 116.94) (R0: +dy, MX: -dy).  The existing per-row offset of the tap from the
  pin (R0 +0.129/-0.209, MX +0.129/+0.257) is kept, so only the entry datum moves.  insertion_ps / insertion_ff_ps
  stay the signed-view numbers (298.4 / 243.2) until the new VSW view is signed off (its pin->register mean replaces
  them then).  plan_s13r2.json is rewritten by exact textual xy replacement of those 74 rows only.
usage: python3 delta_vsw_clkc_1029.py   (asserts exact old forms; a second run refuses)
"""
import hashlib
import json
import re
from pathlib import Path

S81 = Path(__file__).resolve().parent
PINS = S81 / "inputs/core_pins/ot_s81sl_vsw_tpl.json"
LEF = S81 / "cores/leaf/lef/ot_s81sl_vsw_tpl.lef"
PLAN = S81 / "plan_s13r2.json"
W, H = 224.64, 224.64
OLD = (56.652, 0.24)
NEW = (107.484, 117.18)
PIN_W, PIN_L = 0.048, 0.48
ISLAND = (105.30, 115.02, 109.62, 119.34)
TAP = "u_lf.u_vsw.clk"
N_TAPS = 74


def rect():
    x, y = NEW
    k = (x - 0.012) / 0.048
    assert abs(k - round(k)) < 1e-6, ("off M5 track", x)
    r = (x - PIN_W / 2, y - PIN_L / 2, x + PIN_W / 2, y + PIN_L / 2)
    assert ISLAND[0] < r[0] and r[2] < ISLAND[2] and ISLAND[1] < r[1] and r[3] < ISLAND[3]
    return r


def edit_pins():
    txt = PINS.read_text()
    old = '   "name": "clk",\n   "layer": "M5",\n   "x": %g,\n   "y": %g\n' % OLD
    assert txt.count(old) == 1, "clk entry not in the expected form"
    d0 = json.loads(txt)
    txt = txt.replace(old, '   "name": "clk",\n   "layer": "M5",\n   "x": %g,\n   "y": %g\n' % NEW)
    d = json.loads(txt)
    d["source"] += ("; S81 source-pin event DIE-S81-32 2026-10-29 (delta_vsw_clkc_1029.py): clk M5 S face "
                    "(56.652,0.24) -> M5 interior slice entry (107.484,117.18) 0.048x0.48 face C; 74 early taps moved")
    d["pinhash"] = hashlib.sha256(json.dumps(d["pins"], sort_keys=True).encode()).hexdigest()[:12]
    txt = txt.replace(json.dumps(d0["source"])[1:-1], json.dumps(d["source"])[1:-1], 1)
    assert txt.count('"pinhash": "%s"' % d0["pinhash"]) == 1
    txt = txt.replace('"pinhash": "%s"' % d0["pinhash"], '"pinhash": "%s"' % d["pinhash"], 1)
    assert json.loads(txt) == d
    PINS.write_text(txt)
    return d0["pinhash"], d["pinhash"]


def edit_lef():
    txt = LEF.read_text()
    old = ("  PIN clk\n    DIRECTION INPUT ;\n    USE SIGNAL ;\n    PORT\n      LAYER M5 ;\n"
           "        RECT 56.628000 0.000000 56.676000 0.480000 ;\n    END\n  END clk\n")
    assert txt.count(old) == 1, "clk PORT not in the expected form"
    assert not re.search(r"^\s*LAYER M[6-9] ;", txt.split("\n  OBS\n", 1)[1], re.M), "plan LEF obstructs above M5"
    x0, y0, x1, y1 = rect()
    new = ("  PIN clk\n    DIRECTION INPUT ;\n    USE SIGNAL ;\n    PORT\n      LAYER M5 ;\n"
           f"        RECT {x0:.6f} {y0:.6f} {x1:.6f} {y1:.6f} ;\n    END\n  END clk\n")
    LEF.write_text(txt.replace(old, new))


def fmt(v):
    return repr(round(v, 3))


def edit_plan():
    txt = PLAN.read_text()
    p = json.loads(txt)
    dx, dy = NEW[0] - OLD[0], NEW[1] - OLD[1]
    moves = {}
    for tn, t in p["partition_types"].items():
        hc = {h["inst"]: h for h in t.get("hard_cores", []) if h["module"] == "ot_s81sl_vsw"}
        for tp in (t.get("clock") or {}).get("taps", []) or []:
            if tp.get("kind") != "core" or tp.get("name") != TAP:
                continue
            h = hc["u_lf.u_vsw"]
            o = h["orient"]
            assert o in ("R0", "MX"), (tn, o)
            ox, oy = h["origin_um"]
            # old-form assert: the tap sits at the S/N face pin with the recorded per-orient offset
            ex = ox + OLD[0] + 0.129
            ey = oy + OLD[1] - 0.209 if o == "R0" else oy + H - OLD[1] + 0.257
            assert abs(tp["xy"][0] - ex) < 2e-3 and abs(tp["xy"][1] - ey) < 2e-3, (tn, tp["xy"], ex, ey)
            nx, ny = tp["xy"][0] + dx, tp["xy"][1] + (dy if o == "R0" else -dy)
            assert ox < nx < ox + W and oy < ny < oy + H, (tn, nx, ny)
            moves[tn] = (tp["xy"], [round(nx, 3), round(ny, 3)])
            tp["xy"] = [round(nx, 3), round(ny, 3)]
    assert len(moves) == N_TAPS, len(moves)
    # textual replacement of exactly these 74 rows: '"name": "u_lf.u_vsw.clk", "kind": "core", "xy": [x, y]'
    pat = re.compile(r'("name": "u_lf\.u_vsw\.clk",\s*"kind": "core",\s*"xy": \[\s*)([-0-9.]+)(,\s*)([-0-9.]+)(\s*\])')
    hits = pat.findall(txt)
    assert len(hits) == N_TAPS, ("textual tap rows", len(hits))
    new = {}
    for tn, (o, n) in moves.items():
        new.setdefault((round(o[0], 3), round(o[1], 3)), set()).add(tuple(n))
    def sub(m):
        k = (round(float(m.group(2)), 3), round(float(m.group(4)), 3))
        (n,) = new[k]
        return f"{m.group(1)}{fmt(n[0])}{m.group(3)}{fmt(n[1])}{m.group(5)}"
    txt2 = pat.sub(sub, txt)
    assert json.loads(txt2) == p, "textual edit != structural edit"
    PLAN.write_text(txt2)
    return len(moves)


if __name__ == "__main__":
    h = edit_pins()
    edit_lef()
    n = edit_plan()
    print("ot_s81sl_vsw clk", OLD, "->", NEW, "rect", tuple(round(v, 3) for v in rect()), "pinhash", h, "taps moved", n)
