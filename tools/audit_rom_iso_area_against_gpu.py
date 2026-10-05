#!/usr/bin/env python3
"""The ROM products' iso-area comparison, which the 826 mm2 frame cannot express.

``tools/audit_device_level_iso_area.py`` charges our side for memory and asks what
the design delivers inside the A100's own 826 mm2.  For the HBM/SRAM products that
is the right question and the answer is 2.77x-2.97x.  For the ROM products it is
the WRONG question: 16 GiB of on-die mask ROM is 946 mm2 at the optimistic
density, so a ROM product is larger than a GPU die by construction and "does not
fit" says nothing about whether it is a good design.

The right frame is matched SILICON AREA at system level -- how much silicon does
each side need to serve the same model, and what does each deliver on it -- and
``results/roofline/n5_vs_b200/analytical.json`` already computes it: every
comparison pairs a ROM design point with the GPU configuration of the same
silicon area, reports the aggregate tokens per second of both, the energy per
token of both, and **which constraint binds the GPU**.

This audit extracts that for the design points the committed capabilities
correspond to, rather than for the whole 4,608-entry sweep, because the sweep's
extremes (hundreds of devices, 555,000 mm2) are about the GPU's own scaling limits
and not about ROM density -- at those widths the GPU is bound by ``link_latency``
and the ratio says more about interconnect than about weights.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "opentallas.derived.rom_iso_area_against_gpu.v1"
TOOL = "tools/audit_rom_iso_area_against_gpu.py"
ANALYTICAL = ROOT / "results/roofline/n5_vs_b200/analytical.json"

#: The geometries the committed ABI 3.0 capabilities correspond to.  A sweep point
#: at 340 devices is not one of the nine cells.
SHIPPED_GEOMETRIES = (
    "wafer-tensor-x1",
    "array-tensor-x32",
    "array-hybrid-x32",
    "array-hybrid-x30",
    "array-pipeline-x6",
    "array-pipeline-x7",
    "array-pipeline-x8",
)



def _load_study_artifact(path):
    """A roofline study as one dict: ``analytical.json`` plus its ``points.json``
    shard and the de-duplicated design provenance (see
    ``opentallas.roofline.load_study_artifact``, which this mirrors so the tool
    stays standard-library only)."""

    path = Path(path)
    body = json.loads(path.read_text())
    shard = body.pop("points_file", None)
    if shard:
        body["points"] = json.loads((path.parent / shard).read_text())
    table = body.pop("provenance_table", None)
    if table:
        for design in body.get("designs", ()):
            reference = design.get("provenance")
            if isinstance(reference, str) and reference in table:
                design["provenance"] = table[reference]
    return body

def _git(*args: str) -> str:
    return subprocess.run(
        ("git", *args), cwd=ROOT, capture_output=True, text=True, check=False
    ).stdout.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results/derived/rom_iso_area_against_gpu.json",
    )
    arguments = parser.parse_args(argv)

    body = _load_study_artifact(ANALYTICAL)
    usable = [
        entry
        for entry in body["comparisons"]
        if entry.get("iso_area_gpu_feasible")
        and entry.get("aggregate_speed_ratio") is not None
    ]
    grouped: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for entry in usable:
        grouped[entry["rom_design"]].append(entry)

    def summarise(entries: list[dict[str, Any]]) -> dict[str, Any]:
        best = max(entries, key=lambda e: e["aggregate_speed_ratio"])
        worst = min(entries, key=lambda e: e["aggregate_speed_ratio"])
        return {
            "operating_points": len(entries),
            "best_aggregate_speed_ratio": best["aggregate_speed_ratio"],
            "worst_aggregate_speed_ratio": worst["aggregate_speed_ratio"],
            "best_energy_per_token_ratio": best["energy_per_token_ratio"],
            "rom_silicon_area_mm2": best["rom_silicon_area_mm2"],
            "iso_area_gpu_silicon_area_mm2": best["iso_area_gpu_silicon_area_mm2"],
            "iso_area_gpu_design": best["iso_area_gpu_design"],
            "iso_area_gpu_binding_constraint": best["iso_area_gpu_binding_constraint"],
            "above_parity_at_best": best["aggregate_speed_ratio"] > 1.0,
            "above_parity_across_its_whole_range": worst["aggregate_speed_ratio"] > 1.0,
        }

    shipped = {
        design: summarise(entries)
        for design, entries in sorted(grouped.items())
        if any(geometry in design for geometry in SHIPPED_GEOMETRIES)
    }
    everything = [summarise(entries) for entries in grouped.values()]
    all_best = [row["best_aggregate_speed_ratio"] for row in everything]

    report = {
        "schema": SCHEMA,
        "producer": {"tool": TOOL, "git": {"commit": _git("rev-parse", "HEAD")}},
        "question": (
            "at MATCHED SILICON AREA, how does each ROM design point compare with "
            "the GPU configuration of the same area, and what binds the GPU?"
        ),
        "why_not_the_826_mm2_frame": (
            "a ROM product holds its weights on die, so it is larger than a GPU die "
            "by construction -- 16 GiB is 946 mm2 at the optimistic density. Asking "
            "what it achieves inside 826 mm2 answers a question about packaging, not "
            "about the design. Matched silicon area is the comparison the roofline "
            "already makes and the one the architecture is for."
        ),
        "source": {
            "path": str(ANALYTICAL.relative_to(ROOT)),
            "sha256": hashlib.sha256(ANALYTICAL.read_bytes()).hexdigest(),
            "comparisons_total": len(body["comparisons"]),
            "comparisons_with_a_feasible_pairing_and_a_ratio": len(usable),
            "distinct_rom_designs": len(grouped),
        },
        "across_every_design_point": {
            "designs": len(everything),
            "median_best_aggregate_speed_ratio": statistics.median(all_best),
            "fraction_above_parity_at_best": sum(1 for v in all_best if v > 1.0)
            / len(all_best),
            "caveat": (
                "the largest ratios (up to 416x at 185,000-555,000 mm2) are points "
                "where the GPU is bound by link_latency, which is a statement about "
                "many-device interconnect rather than about ROM; the shipped "
                "geometries below are the ones the nine cells correspond to"
            ),
        },
        "shipped_geometries": shipped,
        "not_a_claim": [
            "analytical, not measured silicon: this is the roofline's model of both "
            "sides, and its inputs carry their own grades",
            "the GPU comparator here is B200-class, as the record's own name says; "
            "the A100 comparison at 826 mm2 is the separate device-level audit",
            "a ratio above one at a design point's BEST operating point is not a "
            "claim about its whole range, which is why the worst is reported beside "
            "it for every row",
        ],
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report["across_every_design_point"], indent=1))
    for design, row in sorted(
        shipped.items(), key=lambda kv: -kv[1]["best_aggregate_speed_ratio"]
    )[:14]:
        print(
            f"  {design[:52]:52s} best {row['best_aggregate_speed_ratio']:7.2f}x "
            f"worst {row['worst_aggregate_speed_ratio']:6.3f}x "
            f"energy {row['best_energy_per_token_ratio']:6.3f}x "
            f"gpu-bound-by {row['iso_area_gpu_binding_constraint']}"
        )
    print(f"-> {arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
