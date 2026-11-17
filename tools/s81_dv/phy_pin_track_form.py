#!/usr/bin/env python3
"""Emit a separate PHY abstract with track-centred physical pin form.

The raw input is preserved verbatim. Signal-pin metal rectangles are translated
without shape changes onto the actual parent tracks. This is an explicit new
version of the generated PHY macro physical contract, not a modification to a
routed child or its GDS. Outline, ports, timing arcs, RTL and cycles are unchanged.
The old abstract remains immutable and does not claim these new pin positions.
"""
import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

PITCH = {"M3": 36, "M4": 48, "M5": 48, "M6": 64, "M7": 64}
OFFSET = {"M3": 9, "M4": 24, "M5": 24, "M6": 32, "M7": 32}
VERTICAL = {"M3", "M5", "M7"}
PIN = re.compile(r"(  PIN (\S+)\n)(.*?)(\n  END \2)", re.S)
RECT = re.compile(r"(\s*RECT )([\d.-]+) ([\d.-]+) ([\d.-]+) ([\d.-]+)( ;)" )


def transform(text, origin_nm=(77760, 4320)):
    changes = []
    shapes = defaultdict(list)
    names = []
    size = re.search(r"SIZE ([\d.]+) BY ([\d.]+)", text)
    bounds = tuple(round(float(x) * 1000) for x in size.groups())

    def pin(m):
        name, body = m[2], m[3]
        if re.search(r"USE (POWER|GROUND)", body):
            return m[0]
        names.append(name)
        layer = re.search(r"LAYER (M\d+) ;", body)[1]
        axis = 0 if layer in VERTICAL else 1
        pitch, offset = PITCH[layer], OFFSET[layer]

        def rect(r):
            old = [round(float(v) * 1000) for v in r.group(2, 3, 4, 5)]
            centre = (old[axis] + old[axis + 2]) // 2
            glob = centre + origin_nm[axis]
            target = offset + round((glob - offset) / pitch) * pitch - origin_nm[axis]
            new = old.copy()
            new[axis] += target - centre
            new[axis + 2] += target - centre
            assert new[2]-new[0] == old[2]-old[0] and new[3]-new[1] == old[3]-old[1]
            assert new[0] >= 0 and new[1] >= 0 and new[2] <= bounds[0] and new[3] <= bounds[1]
            assert (target + origin_nm[axis] - offset) % pitch == 0
            shapes[layer].append((name, new))
            if new != old:
                changes.append({"pin": name, "layer": layer, "old_nm": old, "new_nm": new,
                                "centre_shift_nm": target - centre,
                                "added_area_nm2": (new[2]-new[0])*(new[3]-new[1]) - (old[2]-old[0])*(old[3]-old[1])})
            return r[1] + " ".join(f"{v/1000:.3f}" for v in new) + r[6]

        return m[1] + RECT.sub(rect, body) + m[4]

    out = PIN.sub(pin, text)
    spacing = {}
    for layer, ss in shapes.items():
        axis = 0 if layer in VERTICAL else 1
        ordered = sorted(ss, key=lambda x: x[1][axis])
        gaps = []
        for (an, a), (bn, b) in zip(ordered, ordered[1:]):
            other = 1-axis
            if an != bn and a[other] < b[other+2] and b[other] < a[other+2]:
                gaps.append(b[axis] - a[axis+2])
        spacing[layer] = min(gaps) if gaps else None
        assert not gaps or min(gaps) >= 72, (layer, min(gaps))
    report = {"schema": "opentallas.phy.pin_track_form.v1", "signal_pins": len(names),
              "names_sha256": hashlib.sha256("\n".join(names).encode()).hexdigest(),
              "changed_shapes": len(changes), "old_shapes_contained": False, "old_raw_source_preserved": True, "pin_dimensions_preserved": True,
              "bounds_pass": True, "off_track_access_centres": 0,
              "origin_nm": list(origin_nm), "minimum_same_layer_clearance_nm": spacing,
              "max_centre_shift_nm": max(abs(c["centre_shift_nm"]) for c in changes),
              "max_edge_extension_nm": max(max(abs(a-b) for a,b in zip(c["old_nm"],c["new_nm"])) for c in changes),
              "added_pin_metal_area_um2": sum(c["added_area_nm2"] for c in changes)/1e6,
              "added_cells": 0, "added_cycles": 0, "outline_unchanged": True,
              "contract_basis": "Generated PHY macro abstract, not a routed hard-child/GDS view. Pin moves are explicit new physical contract; timing arcs unchanged, no invented routed timing.",
              "changes": changes}
    return out, report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--origin-x", type=float, default=77.76)
    ap.add_argument("--origin-y", type=float, default=4.32)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    raw = args.source.read_text()
    out, report = transform(raw, tuple(round(x*1000) for x in (args.origin_x,args.origin_y)))
    (args.out / (args.source.stem + ".raw.lef")).write_text(raw)
    (args.out / args.source.name).write_text(out)
    report["source_sha256"] = hashlib.sha256(raw.encode()).hexdigest()
    report["output_sha256"] = hashlib.sha256(out.encode()).hexdigest()
    (args.out / "pin_access.json").write_text(json.dumps(report, indent=1)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k != "changes"}, indent=1))


if __name__ == "__main__":
    main()
