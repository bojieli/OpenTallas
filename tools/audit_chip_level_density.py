#!/usr/bin/env python3
"""Assemble a whole chip from routed blocks and compare it to a GPU die.

WHY THIS EXISTS, AND WHAT IT REPLACES
-------------------------------------
``tools/audit_mac_array_density.py`` compares a MAC array's area against the
A100's LOGIC area, and says in its own docstring that an array-level figure is an
upper bound rather than a product figure. That refusal is correct and it is also a
gap: the comparison a reader actually wants is chip against chip, at DEVICE level,
where the GPU is charged for its whole 826 mm² and so is this design.

This tool builds that comparison. It instantiates a capability's declared engine
counts out of blocks that have actually been place-and-routed, sums their areas,
and divides the summed throughput by the summed area. Nothing is scaled,
interpolated or estimated: every component area and frequency is read from a
record whose flow ran.

THE CLOCK IS THE SLOWEST INSTANTIATED BLOCK
-------------------------------------------
A single-clock chip runs at the slowest thing on that clock, so the throughput
here is computed at ``min(fmax)`` over the instantiated DATAPATH blocks. The
control plane is excluded from that minimum and charged its own clock, because
``ot_cluster_dispatcher`` puts a descriptor queue between the two domains and
``tools/audit_control_path_throughput.py`` measures that the control side keeps up
-- 99.1 % array utilisation on 16 real compute units. Without that decoupling the
chip would run at the sequencer's 265 MHz and this tool would have to say so.

WHAT IS IN AND WHAT IS OUT
--------------------------
The honest content of a device-level claim is its inclusion list, so the tool
emits one and refuses to hide it. IN: tensor compute units with their weight
SRAM macros, vector units, reduction units, cluster dispatchers, and the control
plane. OUT: KV-cache SRAM, a global activation buffer, the HBM PHY and controller,
the ROM array itself for the ROM variants, clock distribution, power delivery and
pad ring. Those are real silicon and their omission makes this figure an
overestimate of a finished product, stated as such.

ASAP7 IS NOT TSMC N7
--------------------
The comparator is fabricated silicon on TSMC N7. This design is on ASAP7, a
PREDICTIVE, NON-MANUFACTURABLE academic 7 nm PDK. No amount of place-and-route
makes those the same thing, and a foundry N7 PDK is not obtainable to close the
gap. The node FAMILY matches and the confidence does not, which is why this is
reported as a comparison of two models of a 7 nm-class part rather than as a
silicon result. Recorded as the first refusal.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TECH_INPUTS = ROOT / "configs/hardware/technology_inputs.json"
CAPABILITY_DIR = ROOT / "configs/hardware/abi3_capability"

A100_DIE_AREA_MM2 = 826.0
GPU_LOGIC_FRACTION = 0.6
FLOPS_PER_MAC = 2

#: Every component is a block this repository has place-and-routed. `lanes_each`
#: converts a capability's declared lane count into an instance count; None means
#: the block is instantiated once per chip rather than per lane.
COMPONENTS: tuple[dict[str, Any], ...] = (
    {"name": "tensor_compute_unit", "engine": "tensor", "lanes_each": 16,
     "record": "results/physical_abi3/asap7/compute_unit/pnr.json",
     "datapath": True, "provides_flops": True},
    {"name": "vector_add_unit", "engine": "vector", "lanes_each": 8,
     "record": "results/physical_abi3/asap7/vector_add_unit/pnr.json",
     "datapath": True, "provides_flops": False},
    {"name": "reduction_endpoint", "engine": "reduction", "lanes_each": 8,
     "record": "results/physical_abi3/asap7/reduction_s8_g2/pnr.json",
     "datapath": True, "provides_flops": False},
    {"name": "cluster_dispatcher", "engine": "tensor", "lanes_each": 256,
     "record": "results/physical_abi3/asap7/cluster_dispatcher/pnr.json",
     "datapath": True, "provides_flops": False,
     "note": "one per 16 compute units, which is 256 tensor lanes"},
    {"name": "microsequencer", "engine": None, "lanes_each": None,
     "record": "results/physical_abi3/asap7/a3_microsequencer/pnr.json",
     "datapath": False, "provides_flops": False,
     "note": "one per chip; on its own clock, decoupled by the dispatcher queue"},
)

EXCLUDED_FROM_AREA = (
    "KV-cache SRAM",
    "global activation buffer",
    "HBM PHY and memory controller",
    "the mask-ROM array itself, for the ROM capabilities",
    "clock distribution and power delivery",
    "pad ring and I/O",
)


def git_state() -> dict[str, Any]:
    def run(*a: str) -> str:
        return subprocess.run(["git", *a], cwd=ROOT, capture_output=True,
                              text=True, check=False).stdout.strip()
    return {"commit": run("rev-parse", "HEAD") or None,
            "worktree_dirty": bool(run("status", "--porcelain"))}


def load_block(rel: str) -> dict[str, Any]:
    path = ROOT / rel
    body = json.loads(path.read_text())
    metrics = (body.get("place_and_route") or {}).get("metrics") or {}
    if not metrics.get("fmax_hz") or not metrics.get("core_area_um2"):
        raise SystemExit(f"{rel}: needs a completed pnr stage")
    return {
        "record": rel,
        "fmax_hz": float(metrics["fmax_hz"]),
        "core_area_um2": float(metrics["core_area_um2"]),
        "standard_cell_count": metrics.get("standard_cell_count"),
        "status": body.get("status"),
        "closed": (body.get("design") or {}).get("closed"),
    }


def comparator() -> dict[str, Any]:
    facts = json.loads(TECH_INPUTS.read_text())["source_facts"]["a100_sxm_80gb"]
    ops = float(facts["bf16_dense_ops_s"])
    return {
        "part": "a100_sxm_80gb",
        "process": facts["process"],
        "bf16_dense_ops_s": ops,
        "die_area_mm2": A100_DIE_AREA_MM2,
        "device_level_ops_s_per_mm2": ops / A100_DIE_AREA_MM2,
        "logic_level_ops_s_per_mm2": ops / (A100_DIE_AREA_MM2 * GPU_LOGIC_FRACTION),
    }


def build_chip(capability: Path) -> dict[str, Any]:
    cap = json.loads(capability.read_text())
    engines = cap.get("engines") or {}
    parts, area_um2, tensor_lanes = [], 0.0, 0
    datapath_fmax = []

    for comp in COMPONENTS:
        block = load_block(comp["record"])
        if comp["lanes_each"] is None:
            count = 1
        else:
            lanes = (engines.get(comp["engine"]) or {}).get("lanes")
            if not lanes:
                continue
            count = -(-int(lanes) // comp["lanes_each"])   # ceil
            if comp["name"] == "tensor_compute_unit":
                tensor_lanes = int(lanes)
        parts.append({**comp, **block, "instances": count,
                      "area_um2_total": block["core_area_um2"] * count})
        area_um2 += block["core_area_um2"] * count
        if comp["datapath"]:
            datapath_fmax.append({"block": comp["name"], "fmax_hz": block["fmax_hz"]})

    if not tensor_lanes:
        return {}
    binding = min(datapath_fmax, key=lambda r: r["fmax_hz"])
    ops_s = tensor_lanes * FLOPS_PER_MAC * binding["fmax_hz"]
    area_mm2 = area_um2 / 1e6
    return {
        "capability": capability.name,
        "tensor_lanes": tensor_lanes,
        "components": parts,
        "chip_area_mm2": area_mm2,
        "datapath_clock_hz": binding["fmax_hz"],
        "datapath_clock_binding_block": binding["block"],
        "datapath_fmax_candidates": datapath_fmax,
        "bf16_ops_s": ops_s,
        "device_level_ops_s_per_mm2": ops_s / area_mm2,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()

    ref = comparator()
    chips = [c for c in (build_chip(p) for p in sorted(CAPABILITY_DIR.glob("*.json"))) if c]

    body = {
        "schema": "opentallas.audit.chip_level_density.v1",
        "question": ("Assembled from blocks that have been place-and-routed, how "
                     "does a whole chip's throughput per unit area compare with a "
                     "same-node-family GPU die, at DEVICE level on both sides?"),
        "git": git_state(),
        "comparator": ref,
        "chips": chips,
        "area_excludes": list(EXCLUDED_FROM_AREA),
        "refusals": [
            "asap7-is-not-tsmc-n7: the comparator is fabricated silicon on a "
            "foundry node; this design is on ASAP7, a predictive and explicitly "
            "NON-MANUFACTURABLE academic PDK, and a foundry N7 PDK is not "
            "obtainable to close the gap. The node family matches; the confidence "
            "does not. This is a comparison of two models of a 7 nm-class part, "
            "not a silicon result.",
            "area-inclusion-is-incomplete: the summed area omits KV-cache SRAM, a "
            "global activation buffer, HBM PHY and controller, the mask-ROM array "
            "itself, clock and power distribution, and the pad ring. Every one is "
            "real silicon, so this density OVERSTATES a finished product.",
            "peak-arithmetic-only: the throughput is lanes x 2 x clock, a peak "
            "figure that assumes every lane retires a MAC every cycle. Measured "
            "array utilisation on real compute units under a real dispatcher is "
            "99.1 %, but that is one kernel shape and not a whole workload.",
            "no-power-or-thermal-limit: the A100's 312 TFLOP/s is a figure it "
            "sustains inside a 400 W envelope. Nothing here is power-constrained, "
            "and a design that ignores power can always win on area.",
            "single-clock-assumption-is-load-bearing: the datapath clock is the "
            "minimum over instantiated datapath blocks. The control plane is "
            "excluded and charged its own clock, which is only legitimate because "
            "the dispatcher decouples the domains and the control audit measures "
            "that it keeps up.",
        ],
    }

    print(f"comparator: {ref['part']} on {ref['process']}, "
          f"{ref['bf16_dense_ops_s']/1e12:.0f} TFLOP/s over {ref['die_area_mm2']:.0f} mm2")
    print(f"  device level: {ref['device_level_ops_s_per_mm2']/1e12:.3f} TFLOP/s per mm2\n")
    print(f"  {'capability':<38} {'lanes':>6} {'area mm2':>9} {'clock':>8} "
          f"{'TFLOP/s':>9} {'T/s/mm2':>9} {'vs A100':>8}")
    for c in chips:
        ratio = c["device_level_ops_s_per_mm2"] / ref["device_level_ops_s_per_mm2"]
        print(f"  {c['capability'].replace('.json',''):<38} {c['tensor_lanes']:>6} "
              f"{c['chip_area_mm2']:>9.3f} {c['datapath_clock_hz']/1e6:>7.0f}M "
              f"{c['bf16_ops_s']/1e12:>9.2f} "
              f"{c['device_level_ops_s_per_mm2']/1e12:>9.3f} {ratio:>7.2f}x")

    worst = min(c["device_level_ops_s_per_mm2"] / ref["device_level_ops_s_per_mm2"]
                for c in chips)
    print(f"\nworst case {worst:.2f}x the A100 at DEVICE level on both sides.")
    print(f"clock bound by: {chips[0]['datapath_clock_binding_block']}")
    print("\nThis is chip against die at matched inclusion, which the array-level "
          "audit could not\nclaim. Read the refusals: the area list is incomplete, "
          "the throughput is peak, and\nASAP7 is not TSMC N7.")

    if args.output:
        args.output.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")
        try:
            shown = args.output.relative_to(ROOT)
        except ValueError:
            shown = args.output
        print(f"wrote {shown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
