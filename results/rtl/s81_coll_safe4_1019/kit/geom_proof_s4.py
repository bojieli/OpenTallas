#!/usr/bin/env python3
"""Geometry proof for dscoll_lane_{w,e}_s4 from the generated floorplan.json (lattice, channels, band, pin faces, reach).
Runs tools/ref_tile/measured_band_fill.lattice_band_errors with a placeholder approver: the only thing not proven
here is ROOT approval and the actual placed-cell census (that needs the gate's placed dump)."""
import json, sys, copy
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tools/ref_tile"))
from measured_band_fill import lattice_band_errors
out = {}
SUF = sys.argv[1] if len(sys.argv) > 1 else "s4"
for side in ("w", "e"):
    k = ROOT / f"physical/ref_tile/dscoll_lane_{side}_{SUF}"
    s, fp = json.loads((k / "spec.json").read_text()), json.loads((k / "floorplan.json").read_text())
    W, H = fp["die"][2], fp["die"][3]
    blocks = [b for b in fp["blocks"] if b["kind"] == "macro"]
    lo, hi = {"s4": (345.6, 385.2), "s4b": (259.2, 288.0)}[SUF]
    q = copy.deepcopy(s)
    q["fill_reason"] = {"lattice_channel_bound": {"why": "proof run", "approved_by": "ROOT", "std_band_y_um": [lo, hi]}}
    errs = lattice_band_errors(q, W, H, blocks, s["std_area_um2"])
    # minimum macro-macro gap and per-channel pin-face contacts (pins on the macro W/E faces: 106 big / 103 small each)
    gaps = []
    for i, a in enumerate(blocks):
        for b in blocks[i + 1:]:
            gx = max(a["x"] - b["x"] - b["w"], b["x"] - a["x"] - a["w"]); gy = max(a["y"] - b["y"] - b["h"], b["y"] - a["y"] - a["h"])
            gaps.append(max(gx, gy))
    cols = sorted({b["x"] for b in blocks})
    chan = []
    for c0, c1 in zip(cols, cols[1:]):
        L = [b for b in blocks if b["x"] == c0]; R = [b for b in blocks if b["x"] == c1]
        width = c1 - max(b["x"] + b["w"] for b in L)
        pins = sum(106 if b["w"] > 33 else 103 for b in L + R)
        chan.append({"x": round(c1 - width, 3), "width_um": round(width, 3), "face_contacts": pins,
                     "m3_m5_tracks": int(width / 0.036) + int(width / 0.048), "use": round(pins / (int(width / 0.036) + int(width / 0.048)), 3)})
    # reach: macro pin face -> nearest band edge (L1, flop placed in the band right under/over the macro channel)
    reach = max(min(abs(b["y"] - hi), abs(b["y"] + b["h"] - lo)) if (b["y"] >= hi or b["y"] + b["h"] <= lo) else 0 for b in blocks)
    reach_far = max((b["y"] - hi) if b["y"] >= hi else (lo - b["y"]) for b in blocks)
    pin_far = max(H - 2.16 - hi, lo - 2.16)
    face = {}
    for p, (a, z) in s["pin_ranges"].items():
        face[p] = round(z - a, 2)
    out[side] = {"die": [W, H], "macros": len(blocks), "lattice_band_errors": errs, "min_macro_gap_um": round(min(gaps), 3),
                 "min_core_edge_um": round(min(min(b["x"], b["y"], W - b["x"] - b["w"], H - b["y"] - b["h"]) for b in blocks) - 2.16, 3),
                 "band": [lo, hi], "band_density_synth": round(s["std_area_um2"] / ((W - 4.32) * (hi - lo)), 4),
                 "pin_face_channels": chan, "macro_to_band_um_near_face": round(reach, 2),
                 "macro_to_band_um_far_corner": round(reach_far, 2), "pin_to_band_um_max": round(pin_far, 2),
                 "bus_pin_density_per_um": {"rx": round(515 / face["rx"], 2), "tx": round(512 / face["tx"], 2),
                                            "lo_d": round(553 / face["lo_d"], 2), "li_d": round(553 / face["li_d"], 2)}}
print(json.dumps(out, indent=1))
