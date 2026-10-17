#!/usr/bin/env python3
"""H-SM 2026-10-16: machine-readable pin file for the A2P SM portrait column F108 (1,939.68 x 6,678.72 um,
witness ab729be8a).  R0 frame (S-quadrant columns); N-quadrant columns place it MX (x unchanged, N<->S).

Windows (H-DIE cut rule: bits x 0.096 / L <= 0.55, <= 6 pins/um):
  N face  xw_en, xw_addr[6:0], xw_grp[6:0], xw_data[2047:0]          x 1578.96 .. 1939.68
  S face  command[191:0], kv_desc[63:0], packet[1098:0], request[42:0] x 1637.28 .. 1881.36   (SM_HBM)
  S face  rv, rrow[11:0], rdata[255:0], fault, schedule_fault         x 1892.16 .. 1939.68   (result)
  E face  clk, rst_n (one regional root; root site in the front column at mid-height), M4
Bit order: ascending x, buses in the listed order, bit 0 first.  N/S pins alternate M3 (pitch 0.036, offset 0.009) /
M5 (pitch 0.048, offset 0.012) on legal tracks, as tools/ref_tile/spread_face_pins.py; pin rectangles M3 0.018x0.144,
M5 0.024x0.192, M4 0.192x0.024.
"""
import json
from pathlib import Path
W, H = 1939.68, 6678.72
PITCH = {"M3": 0.036, "M5": 0.048, "M4": 0.048}
OFF = {"M3": 0.009, "M5": 0.012, "M4": 0.012}
SIZE = {"M3": [0.018, 0.144], "M5": [0.024, 0.192], "M4": [0.192, 0.024]}
GROUPS = [
    ("xw", "N", 1578.96, 1939.68, [("xw_en", 1), ("xw_addr", 7), ("xw_grp", 7), ("xw_data", 2048)], "input"),
    ("sm_hbm", "S", 1637.28, 1881.36, [("command", 192), ("kv_desc", 64), ("packet", 1099), ("request", 43)], None),
    ("result", "S", 1892.16, 1939.68, [("rv", 1), ("rrow", 12), ("rdata", 256), ("fault", 1), ("schedule_fault", 1)], "output"),
]
DIR = {"request": "output"}


def snap(x, layer):
    p, o = PITCH[layer], OFF[layer]
    return round(round((x - o) / p) * p + o, 3)


pins, windows = [], []
for gname, face, lo, hi, buses, gdir in GROUPS:
    bits = [(n, i, w) for n, w in buses for i in range(w)]
    n = len(bits); L = hi - lo; step = L / n
    used = {"M3": [], "M5": []}
    for k, (name, i, w) in enumerate(bits):
        layer = "M5" if k % 2 == 0 else "M3"
        x = snap(lo + (k + 0.5) * step, layer)
        assert lo <= x <= hi
        used[layer].append(x)
        pins.append(dict(pin=f"{name}[{i}]" if w > 1 else name, port=name, bit=i, group=gname, face=face, layer=layer,
                         direction=DIR.get(name, gdir or "input"), x=x, y=(H if face == "N" else 0.0), size=SIZE[layer]))
    for layer, xs in used.items():
        xs.sort(); gaps = [b - a for a, b in zip(xs, xs[1:])]
        assert min(gaps) >= 2 * PITCH[layer] - 1e-9, (gname, layer, min(gaps))
    windows.append(dict(group=gname, face=face, x=[lo, hi], length_um=round(L, 3), bits=n,
                        pins_per_um=round(n / L, 3), cut=round(n * 0.096 / L, 4),
                        min_same_layer_gap_um={l: round(min(b - a for a, b in zip(sorted(v), sorted(v)[1:])), 3) for l, v in used.items()},
                        bus_order=[f"{b}[{w - 1}:0]" if w > 1 else b for b, w in buses]))
ym = round(round((H / 2 - OFF["M4"]) / PITCH["M4"]) * PITCH["M4"] + OFF["M4"], 3)
for k, (name, d) in enumerate([("clk", "input"), ("rst_n", "input")]):
    pins.append(dict(pin=name, port=name, bit=0, group="clock_reset", face="E", layer="M4", direction=d,
                     x=W, y=round(ym + k * 4.32, 3), size=SIZE["M4"]))
windows.append(dict(group="clock_reset", face="E", y=[ym, round(ym + 4.32, 3)], bits=2,
                    note="one regional root (DIE-CLOCK 640fa898f); root site in the front column at mid-height; rst_n "
                         "registered at the front, regional sync reset tree inside the column"))
out = dict(schema="opentallas.hbm.sm_column_pins.v1", frame="F108 portrait column (witness ab729be8a)",
           outline_um=[W, H], orientation_note="R0 = S-quadrant columns; N-quadrant columns are MX (x unchanged, N<->S faces)",
           top="ot_hbm_accel_smh_attn (column frame)", windows=windows, pin_count=len(pins), pins=pins)
D = Path(__file__).resolve().parents[2] / "results/arch/hbm_die_v15/sm_portrait_column_1016"
D.mkdir(parents=True, exist_ok=True)
(D / "column_pins.json").write_text(json.dumps(out, indent=0) + "\n")
print(json.dumps(windows, indent=1)); print("pins", len(pins))
