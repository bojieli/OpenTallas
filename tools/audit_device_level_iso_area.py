#!/usr/bin/env python3
"""The A100 comparison with MEMORY ON BOTH SIDES, which the chip-level audit is not.

``results/derived/chip_level_density_audit.json`` reports 2.23x to 2.74x against
the A100 at "device level", and its own ``area_excludes`` field lists what that
leaves out on our side: the KV-cache SRAM, the global activation buffer, the HBM
PHY and controller, and -- for the ROM capabilities -- the mask-ROM array itself.
The A100's 826 mm2 excludes none of its equivalents: its L2 and register files,
and its HBM PHYs, are on that die.  So the published ratio is a
logic-assembly-to-whole-die comparison wearing a device-level label, and every
statement of it in this repository has had to carry that qualification in prose.

This audit removes the qualification by charging our side for the same
categories, from anchors that are already in the tree:

*   **SRAM** at the density of the ASAP7 macros the design actually places.
    ``fakeram_256x128`` occupies 1,404.48 um2 as routed inside
    ``ot_compute_unit`` and holds 4,096 bytes, which is 2.9164e6 bytes/mm2;
    ``fakeram7_128x64`` is 722.305 um2 for 1,024 bytes, 1.4177e6 bytes/mm2.  The
    large macro is the anchor -- a multi-megabyte array amortises periphery the
    way a 1 KiB macro cannot -- and the small one is reported beside it as the
    pessimistic bound rather than hidden.
*   **HBM PHY and controller** at ``technology.json``'s
    ``hbm.hbm2e.phy_area_mm2_per_stack``, 10.0 mm2, graded ``assumed`` there
    with the note that 1024-bit PHYs are commonly quoted between 8 and 15 mm2 at
    7 nm class.  The sweep is reported.
*   **The mask-ROM array** at the two graded densities the ROM program already
    carries: the fabricated 28 nm anchor (8.928 Mbit/mm2 = 1.116e6 bytes/mm2) and
    the published 3D-metal evaluation (20.7e6 bytes/mm2).  A ROM capability's
    weights are ON DIE by construction, so excluding them was never defensible.

What is NOT charged, and why: the HBM DRAM stacks themselves, because the A100's
826 mm2 does not include its HBM dies either.  Only the PHY crosses that line.

Nothing here is a silicon claim: ASAP7 is predictive and non-manufacturable, the
PHY figure is an assumption, and the ROM densities are anchors rather than a
fabricated macro of this design.  The point is that the comparison is now
symmetric, and a symmetric number that is worse is worth more than an asymmetric
one that is better.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "opentallas.derived.device_level_iso_area.v1"
TOOL = "tools/audit_device_level_iso_area.py"
CHIP_LEVEL = ROOT / "results/derived/chip_level_density_audit.json"
CAPABILITY_DIR = ROOT / "configs/hardware/abi3_capability"
TECHNOLOGY = ROOT / "configs/hardware/technology.json"

#: Bytes per mm2 of SRAM, from the routed area of the macros this design places.
SRAM_DENSITY_LARGE_MACRO = 4096 / (1404.48e-6)
SRAM_DENSITY_SMALL_MACRO = 1024 / (722.305e-6)

#: Bytes per mm2 of mask ROM, at the two graded anchors the program carries.
ROM_DENSITY_FABRICATED_28NM = 8.928e6 / 8.0
ROM_DENSITY_PUBLISHED_3D_METAL = 20.7e6


def _git(*args: str) -> str:
    return subprocess.run(
        ("git", *args), cwd=ROOT, capture_output=True, text=True, check=False
    ).stdout.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results/derived/device_level_iso_area_audit.json",
    )
    parser.add_argument("--phy-mm2-per-stack", type=float, default=None)
    arguments = parser.parse_args(argv)

    chip_level = json.loads(CHIP_LEVEL.read_text())
    technology = json.loads(TECHNOLOGY.read_text())
    hbm2e = technology["hbm"]["hbm2e"]
    phy_default = float(hbm2e["phy_area_mm2_per_stack"]["value"])
    phy = float(arguments.phy_mm2_per_stack or phy_default)
    stack_bytes = float(hbm2e["stack_capacity_bytes"]["value"])
    comparator = chip_level["comparator"]
    a100_device = float(comparator["device_level_ops_s_per_mm2"])

    rows: list[dict[str, Any]] = []
    for chip in chip_level["chips"]:
        name = chip["capability"]
        body = json.loads((CAPABILITY_DIR / name).read_text())
        capability = body.get("capability", body)
        memory = capability.get("memory", {})
        sram_bytes = int((memory.get("sram") or {}).get("bytes", 0))
        hbm_bytes = int((memory.get("hbm") or {}).get("bytes", 0))
        rom_bytes = int((memory.get("rom") or {}).get("bytes", 0))
        declared_stacks = (memory.get("hbm") or {}).get("physical_stacks")
        stacks = (
            int(declared_stacks)
            if declared_stacks
            else (math.ceil(hbm_bytes / stack_bytes) if hbm_bytes else 0)
        )
        logic = float(chip["chip_area_mm2"])
        ops = float(chip["bf16_ops_s"])

        def total(sram_density: float, rom_density: float) -> dict[str, float]:
            sram_area = sram_bytes / sram_density if sram_bytes else 0.0
            rom_area = rom_bytes / rom_density if rom_bytes else 0.0
            phy_area = stacks * phy
            whole = logic + sram_area + rom_area + phy_area
            return {
                "sram_mm2": sram_area,
                "rom_mm2": rom_area,
                "hbm_phy_mm2": phy_area,
                "device_area_mm2": whole,
                "device_ops_s_per_mm2": ops / whole if whole else 0.0,
                "ratio_vs_a100_device": (ops / whole) / a100_device if whole else 0.0,
            }

        optimistic = total(SRAM_DENSITY_LARGE_MACRO, ROM_DENSITY_PUBLISHED_3D_METAL)
        pessimistic = total(SRAM_DENSITY_SMALL_MACRO, ROM_DENSITY_FABRICATED_28NM)
        rows.append({
            "capability": name,
            "bf16_ops_s": ops,
            "logic_assembly_mm2": logic,
            "published_ratio_logic_only": float(
                chip["device_level_ops_s_per_mm2"]
            ) / a100_device,
            "declared_memory_bytes": {
                "sram": sram_bytes,
                "hbm": hbm_bytes,
                "rom": rom_bytes,
            },
            "hbm_stacks_charged": stacks,
            "with_memory_best_case": optimistic,
            "with_memory_worst_case": pessimistic,
        })

    # -- the iso-area question as actually asked -----------------------------
    #
    # The ratios above answer "how much throughput per mm2 does this chip have",
    # and for a chip whose logic assembly is 0.78 mm2 against 46 mm2 of SRAM and
    # 70 mm2 of HBM PHY the answer is dominated by a memory interface sized for a
    # machine 470x larger than the datapath the audit assembles.  That is a fact
    # about the ASSEMBLY, not about the architecture.
    #
    # "Match performance in iso-area" asks the other question: given the A100's
    # OWN area budget, how much compute does this design fit, and what does it
    # then deliver?  Memory comes out of the same budget, so a design that holds
    # its weights on die pays for them here and one that streams them does not.
    #
    # The compute unit's routed area and post-route frequency are measured, so the
    # only assumption is that the assembly scales linearly in units -- which is
    # what the dispatch-tree campaign measured up to 512 units at 98-99%
    # utilisation, and is stated rather than hidden.
    compute_unit_mm2 = 31524.7e-6
    compute_unit_lanes = 16
    a100_die_mm2 = float(comparator["die_area_mm2"])
    a100_ops = float(comparator["bf16_dense_ops_s"])
    iso = []
    for row in rows:
        for case, label in (
            (row["with_memory_best_case"], "best_case"),
            (row["with_memory_worst_case"], "worst_case"),
        ):
            memory_mm2 = (
                case["sram_mm2"] + case["rom_mm2"] + case["hbm_phy_mm2"]
            )
            remaining = a100_die_mm2 - memory_mm2
            if remaining <= 0:
                iso.append({
                    "capability": row["capability"],
                    "case": label,
                    "memory_mm2": memory_mm2,
                    "fits_in_the_a100_budget": False,
                    "why": (
                        "its declared memory alone exceeds 826 mm2, so no compute "
                        "fits beside it at this density"
                    ),
                })
                continue
            units = remaining / compute_unit_mm2
            lanes = units * compute_unit_lanes
            # Two operations per MAC, at the datapath clock the assembly closed at.
            ops = lanes * 2.0 * float(row_clock := chip_level["chips"][0][
                "datapath_clock_hz"
            ])
            iso.append({
                "capability": row["capability"],
                "case": label,
                "memory_mm2": memory_mm2,
                "fits_in_the_a100_budget": True,
                "compute_area_mm2": remaining,
                "compute_units": units,
                "bf16_lanes": lanes,
                "datapath_clock_hz": row_clock,
                "bf16_ops_s_at_iso_area": ops,
                "a100_bf16_ops_s": a100_ops,
                "ratio_vs_a100_at_iso_area": ops / a100_ops,
            })

    best = [r["with_memory_best_case"]["ratio_vs_a100_device"] for r in rows]
    worst = [r["with_memory_worst_case"]["ratio_vs_a100_device"] for r in rows]
    report = {
        "schema": SCHEMA,
        "producer": {"tool": TOOL, "git": {"commit": _git("rev-parse", "HEAD")}},
        "question": (
            "charged for the same categories the A100's 826 mm2 includes -- SRAM, "
            "the mask-ROM array and the HBM PHY -- what is the device-level "
            "iso-area ratio?"
        ),
        "inputs": {
            "chip_level_audit": {
                "path": str(CHIP_LEVEL.relative_to(ROOT)),
                "sha256": _sha256(CHIP_LEVEL),
            },
            "sram_density_bytes_mm2": {
                "large_macro_fakeram_256x128": SRAM_DENSITY_LARGE_MACRO,
                "small_macro_fakeram7_128x64": SRAM_DENSITY_SMALL_MACRO,
                "basis": (
                    "routed macro area inside ot_compute_unit: 1,404.48 um2 for "
                    "4,096 bytes and 722.305 um2 for 1,024 bytes"
                ),
            },
            "rom_density_bytes_mm2": {
                "fabricated_28nm_anchor": ROM_DENSITY_FABRICATED_28NM,
                "published_3d_metal": ROM_DENSITY_PUBLISHED_3D_METAL,
            },
            "hbm_phy_mm2_per_stack": phy,
            "hbm_phy_grade": hbm2e["phy_area_mm2_per_stack"].get("grade"),
            "hbm_stack_capacity_bytes": stack_bytes,
            "comparator": comparator,
        },
        "not_charged": (
            "the HBM DRAM stacks themselves: the A100's 826 mm2 does not include "
            "its HBM dies either, so only the PHY crosses that line"
        ),
        "headline": {
            "published_logic_only_range": [
                min(r["published_ratio_logic_only"] for r in rows),
                max(r["published_ratio_logic_only"] for r in rows),
            ],
            "with_memory_best_case_range": [min(best), max(best)],
            "with_memory_worst_case_range": [min(worst), max(worst)],
            "above_parity_best_case": all(value > 1.0 for value in best),
            "above_parity_worst_case": all(value > 1.0 for value in worst),
        },
        "iso_area_at_the_a100_budget": {
            "question": (
                "at the A100's own 826 mm2, with memory charged from the same "
                "budget, what does this design deliver against its 312 TFLOP/s?"
            ),
            "compute_unit_mm2": 31524.7e-6,
            "compute_unit_lanes": 16,
            "assumption": (
                "the assembly scales linearly in compute units. The dispatch-tree "
                "campaign measured 98-99% work-conserving utilisation out to 512 "
                "units (8,192 lanes), and the points below reach about 22,500 units "
                "(360,000 lanes) -- a 44x EXTRAPOLATION beyond the measured point. "
                "That is the weakest link in this number and it is stated here "
                "rather than buried: nothing has been built or measured at that "
                "width, and a distributor that stops conserving work at 22,500 "
                "units would reduce the ratio in proportion"
            ),
            "points": iso,
        },
        "chips": rows,
        "not_a_claim": [
            "ASAP7 is a predictive, non-manufacturable PDK and the A100 is TSMC N7 "
            "silicon; this is a design-level comparison, not a silicon one",
            "the HBM PHY area is graded 'assumed' in technology.json and the ROM "
            "densities are anchors, not a fabricated macro of this design",
            "the SRAM density is the PDK's own fakeram macro as routed, which is a "
            "predictive macro rather than a foundry bitcell",
        ],
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report["headline"], indent=1))
    for row in rows:
        print(
            f"  {row['capability']:38s} logic-only {row['published_ratio_logic_only']:6.3f}x"
            f"  with memory {row['with_memory_best_case']['ratio_vs_a100_device']:6.3f}x"
            f" .. {row['with_memory_worst_case']['ratio_vs_a100_device']:6.3f}x"
        )
    print(f"-> {arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
