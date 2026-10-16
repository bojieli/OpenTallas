#!/usr/bin/env python3
"""Prepare local K bridge pins under dimension-only grant; never authorizes a route.
Actual die x/y, orientation, incident reach, clock insertion and final pin grant are
required before kit generation. This file emits a reviewable proposal only.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results/arch/qwen_split_1014/static_k_issuer_1016/physical_draft"


def build():
    pins = {}

    def bus(name, n, face, lo, hi, indices=None):
        ids = list(range(n)) if indices is None else indices
        for j, i in enumerate(ids):
            p = lo + (hi - lo) * (j + 0.5) / len(ids)
            p = (
                0.06 + 0.192 * round((p - 0.06) / 0.192)
                if face in "SN"
                else 0.012 + 0.048 * round((p - 0.012) / 0.048)
            )
            xy = {"W": [0, p], "E": [64.8, p], "N": [p, 280.8], "S": [p, 0]}[face]
            key = name if n == 1 and indices is None else f"{name}[{i}]"
            pins[key] = {
                "face": face,
                "xy": xy,
                "layer": "M5" if face in "SN" else "M4",
            }

    # Long W face faces landing; E faces existing ECTL A. Mirror east-stack homes.
    bus("req_valid", 1, "W", 4, 4.25)
    bus("req_t", 14, "W", 4.5, 8.0)
    bus("req_v", 1, "W", 8.3, 8.55)
    bus("req_epoch", 16, "W", 8.8, 12.8)
    bus("req_layer", 6, "W", 13.1, 14.6)
    bus("rsp_data", 1024, "W", 18, 263.76)
    bus("rsp_valid", 1, "W", 266, 266.25)
    bus("rsp_t", 14, "W", 266.5, 270)
    bus("rsp_v", 1, "W", 270.3, 270.55)
    bus("rsp_epoch", 16, "W", 270.8, 274.8)
    bus("rsp_layer", 6, "W", 275.1, 276.6)
    bus("rq", 17, "E", 4, 8.25)
    # Match actual data-bit identity across the 64.8um bridge; keep rs.valid
    # beside rsp.valid, rather than crossing its wire past all 1024 data bits.
    bus("rs", 1025, "E", 18, 263.76, indices=list(range(1, 1025)))
    bus("rs", 1025, "E", 266, 266.25, indices=[0])
    bus("kgo", 1, "N", 4, 4.3)
    bus("epoch", 16, "N", 6, 14)
    bus("layer", 6, "N", 16, 19)
    bus("rst_n", 1, "N", 22, 22.3)
    bus("ck", 1, "N", 32, 32.3)
    bus("fault", 1, "S", 32, 32.3)
    bus("idle_issuer", 1, "S", 36, 36.3)
    face_stats = {}
    for face in "WENS":
        pp = sorted(
            (v["xy"][1 if face in "WE" else 0], n)
            for n, v in pins.items()
            if v["face"] == face
        )
        gaps = [b[0] - a[0] for a, b in zip(pp, pp[1:])]
        assert min(gaps, default=1) >= (0.096 if face in "WE" else 0.192) - 1e-6, (
            face,
            min(gaps),
        )
        assert all(0 < p < (280.8 if face in "WE" else 64.8) for p, n in pp)
        face_stats[face] = {
            "count": len(pp),
            "min_spacing_um": min(gaps, default=None),
            "cut_at_7tracks_per_um": len(pp) / (7 * (280.8 if face in "WE" else 64.8)),
        }
    OUT.mkdir(parents=True, exist_ok=True)
    lines = []
    for n, v in pins.items():
        x, y = v["xy"]
        size = ".144 .024" if v["face"] in "WE" else ".024 .144"
        lines.append(
            f"place_pin -pin_name {{{n}}} -layer {v['layer']} -location {{{x:.3f} {y:.3f}}} -pin_size {{{size}}}"
        )
    (OUT / "proposed_io.tcl").write_text("\n".join(lines) + "\n")
    d = {
        "status": "PROPOSED_ONLY_DIMENSION_GRANT; NOT_ASSIGNED_DIE_PINS_OR_ROUTE_AUTHORITY",
        "outline_um": [64.8, 280.8],
        "replicas": 32,
        "clock": "core 833.334ps; actual insertion/view not measured",
        "grant": "Q-KVSYS local dimension-only2026-10-16; ECTL home preserved; exact x/y/orientation/clocks and allincident reach await actual v1.5 allocator",
        "faces": face_stats,
        "pins": pins,
        "open": [
            "actual die home/orientation and exact pin grant",
            "allincident pin-to-pin distances/cuts and relay allocation",
            "implemented req-to-rsp segment latency parameter",
            "source-exact CTS/native view TT setup FF hold DRC0",
        ],
    }
    (OUT / "proposal.json").write_text(json.dumps(d, indent=2) + "\n")
    return d


if __name__ == "__main__":
    d = build()
    print(json.dumps(d["faces"], indent=2))
