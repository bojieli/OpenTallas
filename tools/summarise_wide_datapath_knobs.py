#!/usr/bin/env python3
"""Assemble the ASAP7 walk that sets the sequential datapath's two knobs.

``ot_a3_fp32_exp_pos_cr_rne`` routed at **17.5 MHz** and
``ot_a3_fp32_transcendental_cr_rne`` never routed at all -- an eight-hour
synthesis timed out inside ``1_2_yosys`` -- and both had the same cause: wide
products and restoring divisions unrolled into single cycles. Replacing them with
sequential primitives asks two questions that only measurement answers. How many
bits per clock should the restoring divide and the carry-save multiply consume?
And which of the OTHER wide operations in those blocks -- the 163-bit adds, the
170-bit subtract, the comparators, the priority encode inside the rounding -- are
walls of their own, so that fixing the divide leaves a block that still cannot
close?

So each is synthesised and pre-layout timed ALONE, registered in and registered
out, which costs seconds where a route of the parent costs hours. This reads the
per-point records and writes one table.

WHAT THIS IS NOT. Pre-layout timing runs before ``repair_design``, so a net with
hundreds of loads is unbuffered here and its delay is pessimistic -- this
repository has a routed block at 317 MHz whose pre-layout number was 8.18 MHz.
These figures are therefore a RANKING instrument for choosing between structures
at the same widths, not a closure claim. Closure is a routed record.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "opentallas.physical.asap7_wide_datapath_knobs.v1"
TOOL = "tools/summarise_wide_datapath_knobs.py"

#: What each probe MODE measures, in the words of the operation it stands for.
PRIMITIVE_NAMES = {
    0: "163-bit add",
    1: "163-bit increment",
    2: "170-bit subtract",
    3: "170-bit compare, less-than",
    4: "163-bit top-set-bit, linear scan",
    5: "163-bit top-set-bit, two-level group then bit",
    6: "163-bit sticky OR, chained loop",
    7: "163-bit sticky OR, masked reduction",
    8: "161-by-16 constant product",
    9: "163-bit barrel shift",
    10: "170-bit compare against the ln2 constant",
    11: "163-by-161 full product, high half kept",
    12: "170-by-162 x*log2(e), nine bits kept",
    13: "fixed_to_fp32_scaled, power zero",
    14: "fixed_to_fp32_scaled, power variable",
}


def _git_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT,
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def _point(path: Path) -> dict[str, Any]:
    record = json.loads(path.read_text())
    timing = record.get("static_timing") or {}
    synthesis = record.get("synthesis") or {}
    design = record.get("design") or {}
    fmax = timing.get("fmax_hz")
    return {
        "record": str(path.relative_to(ROOT)),
        "top": design.get("top") or design.get("block"),
        "parameters": design.get("parameters") or {},
        "target_clock_period_ns": record.get("target_clock_period_ns"),
        "fmax_mhz": None if not fmax else round(fmax / 1e6, 1),
        "critical_path_ns": timing.get("critical_path_ns"),
        "cell_area_um2": synthesis.get("cell_area_um2"),
        "cell_count": synthesis.get("cell_count"),
        "sequential_cell_count": synthesis.get("sequential_cell_count"),
        "sources": design.get("sources") or [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--points",
        type=Path,
        default=ROOT / "results/physical_abi3/asap7/wide_datapath_knobs",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results/physical_abi3/asap7/wide_datapath_knobs.json",
    )
    args = parser.parse_args()

    divide: list[dict[str, Any]] = []
    multiply: list[dict[str, Any]] = []
    primitives: list[dict[str, Any]] = []
    for path in sorted(args.points.glob("*.json")):
        point = _point(path)
        name = path.stem
        if (match := re.fullmatch(r"div_bits(\d+)", name)):
            point["bits_per_step"] = int(match.group(1))
            divide.append(point)
        elif (match := re.fullmatch(r"mul_bits(\d+)", name)):
            point["bits_per_step"] = int(match.group(1))
            multiply.append(point)
        elif (match := re.fullmatch(r"primitive_mode(\d+)", name)):
            mode = int(match.group(1))
            point["mode"] = mode
            point["primitive"] = PRIMITIVE_NAMES.get(mode, "unnamed")
            primitives.append(point)
        else:
            raise SystemExit(f"unrecognised point file: {path.name}")

    divide.sort(key=lambda p: p["bits_per_step"])
    multiply.sort(key=lambda p: p["bits_per_step"])
    primitives.sort(key=lambda p: p["mode"])

    def peak(points: list[dict[str, Any]]) -> dict[str, Any] | None:
        rated = [p for p in points if p["fmax_mhz"]]
        if not rated:
            return None
        best = max(rated, key=lambda p: p["fmax_mhz"])
        return {"bits_per_step": best["bits_per_step"], "fmax_mhz": best["fmax_mhz"]}

    #: The slowest primitive that is NOT one of the two being replaced is the
    #: ceiling the rewrite cannot lift without changing what the block computes.
    ceiling = None
    rated = [p for p in primitives if p["fmax_mhz"] and p["mode"] not in (11, 12)]
    if rated:
        worst = min(rated, key=lambda p: p["fmax_mhz"])
        ceiling = {
            "primitive": worst["primitive"],
            "fmax_mhz": worst["fmax_mhz"],
            "meaning": (
                "no amount of sequencing the products and divisions lifts the "
                "block above this, because this operation is what the arithmetic "
                "IS rather than how it is scheduled"
            ),
        }

    report = {
        "schema": SCHEMA,
        "producer": {"tool": TOOL, "git": {"commit": _git_commit()}},
        "view": "asap7",
        "stages": "synth,sta",
        "basis": (
            "pinned Yosys plus pinned ABC mapped to the ASAP7 TT liberty, then "
            "pinned OpenSTA on the mapped netlist; each point is one top module "
            "synthesised alone with registered inputs and outputs"
        ),
        "not_a_claim": [
            "pre-layout timing runs BEFORE repair_design, so a high-fanout net is "
            "unbuffered and its delay is pessimistic; this repository has a routed "
            "block at 317 MHz whose pre-layout figure was 8.18 MHz",
            "these numbers rank structures at equal widths and choose a knob; "
            "closure is a routed record and nothing here is one",
            "the walk is not monotonic in bits per step, because ABC maps each "
            "point independently and picks a different adder structure; the peak "
            "is the measurement, not a fitted law",
        ],
        "restoring_divide_small_divisor": {
            "module": "rtl/lib/ot_wide_div_small_seq.sv",
            "width": 163,
            "divisor_bits": 9,
            "points": divide,
            "peak": peak(divide),
        },
        "carry_save_multiply": {
            "module": "rtl/lib/ot_wide_mul_seq.sv",
            "operands": "163 by 161, low 160 product bits OR-reduced",
            "points": multiply,
            "peak": peak(multiply),
        },
        "other_wide_primitives": {
            "vehicle": "rtl/test/ot_wide_carry_probe.sv",
            "points": primitives,
            "ceiling": ceiling,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    print("restoring divide, bits per clock:")
    for point in divide:
        print(f"  {point['bits_per_step']:4d}  {point['fmax_mhz'] or 0:7.1f} MHz"
              f"  {point['cell_area_um2'] or 0:9.1f} um2")
    print("carry-save multiply, bits per clock:")
    for point in multiply:
        print(f"  {point['bits_per_step']:4d}  {point['fmax_mhz'] or 0:7.1f} MHz"
              f"  {point['cell_area_um2'] or 0:9.1f} um2")
    print("every other wide operation in those blocks:")
    for point in primitives:
        print(f"  {point['primitive']:42} {point['fmax_mhz'] or 0:7.1f} MHz")
    if ceiling:
        print(f"-> ceiling the rewrite cannot lift: {ceiling['primitive']} at "
              f"{ceiling['fmax_mhz']} MHz")
    print(f"-> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
