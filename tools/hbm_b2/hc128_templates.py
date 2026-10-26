#!/usr/bin/env python3
"""W128 HC three-master pin/placement template, M5 hard-core ceiling.

The exact exported masters are recovered from the existing qualified structural
cuts. This tool makes their physical interface explicit without substituting
them for a W64 parent whose per-bit cut wiring has not yet been regenerated.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

OUTLINES = {"ot_hbm_hc_bank128_pair_core": (250.56, 267.84),
            "ot_hbm_hc_bank128_pair_first_core": (250.56, 267.84),
            "ot_hbm_hc_subtree32_core": (220.32, 220.32)}


def bits(name, n):
    return [name] if n == 1 else [f"{name}[{i}]" for i in range(n)]


def face(names, side, w, h, lo=8.64, hi=None):
    length = h if side in "WE" else w
    hi = length - 8.64 if hi is None else hi
    layer = "M4" if side in "WE" else "M5"
    used, pins = set(), []
    for i, name in enumerate(names):
        k = round((lo + (i + .5) * (hi - lo) / len(names) - .024) / .048)
        if k in used:
            raise ValueError(f"{side} pin band over capacity")
        used.add(k)
        pos = round(.024 + k * .048, 6)
        x, y = {"W": (.019, pos), "E": (w - .019, pos),
                "S": (pos, .019), "N": (pos, h - .019)}[side]
        pins.append(dict(name=name, layer=layer, x=round(x, 6), y=round(y, 6)))
    return pins


def template(module):
    w, h = OUTLINES[module]
    if "subtree" in module:
        return face(bits("data", 1024) + ["valid_in", "clk", "rst_n"], "N", w, h) + face(
            bits("sum", 32) + ["valid_out"] + bits("node_fault", 31), "S", w, h)
    p = []
    if "first" not in module:
        p += face(bits("sum_in", 512), "W", w, h)
    p += face(bits("sum_out", 512), "E", w, h)
    controls = bits("write_data", 512) + bits("write_addr", 10) + bits("weight_addr", 10) + bits("x_addr", 7)
    controls += bits("lane_valid", 16) + bits("square", 16)
    controls += ["go", "weight_read", "weight_we0", "weight_we1", "x_read", "x_write", "clk", "rst_n"]
    p += face(controls, "N", w, h)
    p += face(bits("fault", 2), "S", w, h)
    return p


def placements(tn, outline, first=False, parent_origin=(0, 0)):
    """Eight same-column pairs; actual B1's narrowest 380.16x2920.32 fits.

    Keep a full 17.28um outer band and use the remaining height for row channels.
    The exact parent instance names are part of the outstanding cut-map contract.
    """
    w, h = outline
    if w < 250.56 + 2 * 17.28 or h < 8 * 267.84 + 9 * 17.28:
        raise ValueError(f"{tn}: native pair stack does not fit")
    gap = math.floor((h - 8 * 267.84 - 2 * 17.28) / 7 / 8.64) * 8.64
    module = "ot_hbm_hc_bank128_pair_first_core" if first else "ot_hbm_hc_bank128_pair_core"
    # 8.64um grid keeps core rows and halo boundaries reproducible.
    return [dict(pair=k, module=module, origin_um=[25.92, round(17.28 + k * (267.84 + gap), 6)],
                 outline_um=[250.56, 267.84], obs_max="M5", halo_um=8.64) for k in range(8)]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plan", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    raw = json.loads(a.plan.read_text())
    a.out.mkdir(parents=True, exist_ok=True)
    manifest = dict(schema="opentallas.hbm.hc128_templates.v1", qualification="PARENT_BIND_PENDING",
                    source_cut="57735a47793c58046dc2d3c0bef4ac5a6bf7ca1f", added_cut_cycles=0,
                    routing_ceiling="M5", masters={}, bank_placements={})
    for module, outline in OUTLINES.items():
        pins = template(module)
        path = a.out / (module + "_pins.json")
        path.write_text(json.dumps(pins) + "\n")
        manifest["masters"][module] = dict(outline_um=list(outline), pins=len(pins),
                pins_file=path.name, pins_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), obs_max="M5")
    for tn, t in raw["partition_types"].items():
        if tn in {"q_b000", "q_b001", "q_b002", "q_b003", "q_b010", "q_b011", "q_b012", "q_b013"}:
            manifest["bank_placements"][tn] = placements(tn, t["outline_um"], first=tn == "q_b000")
    if len(manifest["bank_placements"]) != 8:
        raise ValueError("expected exactly eight native bank types")
    manifest["pending"] = ["exact_native_parent_cut_maps", "perbit_routing_and_geometry_review",
                            "rebuild_core_views_at_M5", "die_GRT_STA_clock_and_token"]
    (a.out / "templates.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(json.dumps({m: p["pins"] for m, p in manifest["masters"].items()}))


if __name__ == "__main__":
    main()
