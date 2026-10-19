#!/usr/bin/env python3
"""Generate the order FIFO's distinct, four-M4-track-pitch SRAM abstract.

Run on an admitted fleet host from a source-pinned checkout. No shared compiler
defaults change. This is a calibrated analytical macro, not a transistor layout.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/mem_compiler"))
import asap7
import sram_gen

NAME = "ot_sram_1r1w_32x128_m1_p192"
asap7.METAL["pin_pitch_um"] = 0.192
sheet = sram_gen.compile_macro(
    sram_gen.SramSpec(NAME, words=32, bits=128, mux=1, ports="1r1w"),
    ROOT / "physical/asap7_memory_macros",
)
d = ROOT / "physical/asap7_memory_macros" / NAME
w = sheet["area"]["macro_width_um"]
h = sheet["area"]["macro_height_um"]
lef = (d / f"{NAME}.lef").read_text()
faces = {"W": [], "E": []}
for name, block in re.findall(r"  PIN (\S+)\n(.*?)  END \1", lef, re.S):
    if "USE POWER" in block or "USE GROUND" in block:
        continue
    rect = re.search(r"RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)", block)
    x0, y0, x1, y1 = map(float, rect.groups())
    faces["W" if x0 < w / 2 else "E"].append((name, (y0+y1)/2))
audit = {}
for face, pins in faces.items():
    ys = sorted(y for _, y in pins)
    pitch = min(b-a for a,b in zip(ys, ys[1:]))
    assert len(pins)/h <= 6 and pitch >= 1/6 - 1e-9
    audit[face] = {"pins": len(pins), "pins_per_um": len(pins)/h,
                   "minimum_pin_pitch_um": pitch}
manifest = {
    "schema": "opentallas.order-sram-safe.v1",
    "source_commit": os.environ.get("SOURCE_COMMIT", "unrecorded"),
    "generator_host": socket.gethostname(),
    "macro": NAME, "instances": 6,
    "spec": sheet["spec"], "area": sheet["area"],
    "pin_pitch_um": 0.192, "pin_layer": "M4", "faces": audit,
    "timing": sheet["timing"], "claim_boundary": sheet["claim_boundary"],
    "compiler_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((ROOT / "tools/mem_compiler").glob("*.py"))},
    "views": sheet["views"],
    "placement_candidate": {
        "outline_um": [302.4, 259.2],
        "macro_origins_um": [[x,y] for y in (43.2,129.6) for x in (43.2,129.6,216)],
        "macro_orientation": "R0",
        "outer_macro_gaps_um": {"west":43.2,"south":43.2,"east":302.4-(216+w)},
        "maximum_outline_diagonal_um": (302.4**2+259.2**2)**0.5,
        "stdcell_area_limit_at_65pct_um2": 302.4*64.8*0.65,
        "horizontal_macro_gap_um": 86.4-w,
        "vertical_macro_gap_um": 86.4-h,
        "full_width_stdcell_band_um": [0,194.4,302.4,259.2],
        "macro_to_stdcell_band_gap_um": 194.4-(129.6+h),
        "baseline_stdcell_area_um2": 13858,
        "baseline_stdcell_band_utilization": 13858/(302.4*64.8),
        "area_um2": 302.4*259.2,
        "area_change_vs_original_172p8_square": 302.4*259.2/(172.8**2)-1,
        "qualification": "candidate only; synthesis, exact placement, routing, SS/FF and registered reach remain required",
    },
}
(Path(__file__).parent / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True)+"\n")
print(json.dumps({"macro": NAME, "width_um": w, "height_um": h, "faces": audit}))
