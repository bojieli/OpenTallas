#!/usr/bin/env python3
"""Every ASAP7 physical record in the tree, and which ones close.

The ASAP7 evidence is 191 records across 36 block directories, written one run at
a time over months, and no single place says how much of the design is actually
routed and closed -- so "is there physical implementation work" got answered from
whichever record a reader happened to open.  This audit reads them all and states,
per record: the block, the flow stages that ran, the target period, whether the
routed netlist closed, the post-route fmax, the core area, and when it is NOT
closed, the reason the record itself gives.

Three distinctions it keeps, because each one has been misread at least once:

*   ``closed`` is not ``status``.  A record's ``status`` is the engineering
    verdict of the stages that ran; ``design.closed`` additionally requires the
    routed netlist to carry zero max-slew, max-cap and max-fanout violations.  A
    design can have POSITIVE setup and hold slack, zero DRC and zero antenna
    violations and still report ``closed=False`` for two max-slew violations --
    measured, on the half-depth compute unit before a slew margin was applied.
*   A ``sta``-only record is PRE-LAYOUT.  It is not a closure statement about
    silicon and is reported in its own bucket rather than counted with the routed
    ones.
*   ASAP7 is a predictive, non-manufacturable academic PDK.  Nothing here is a
    silicon claim, and the refusal travels with the artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "opentallas.physical.asap7_closure_matrix.v1"
TOOL = "tools/audit_asap7_closure_matrix.py"


def _git(*args: str) -> str:
    return subprocess.run(
        ("git", *args), cwd=ROOT, capture_output=True, text=True, check=False
    ).stdout.strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1 << 22):
            digest.update(block)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--view", default="asap7")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results/physical_abi3/asap7_closure_matrix.json",
    )
    arguments = parser.parse_args(argv)

    base = ROOT / "results/physical_abi3" / arguments.view
    rows: list[dict[str, Any]] = []
    for path in sorted(base.rglob("*.json")):
        if "artifacts" in path.parts:
            continue
        try:
            body = json.loads(path.read_text())
        except ValueError:
            continue
        design = body.get("design")
        if not isinstance(design, dict):
            continue
        stages = tuple(body.get("stages_completed") or ())
        routed = "pnr" in stages or "place_and_route" in stages
        metrics = (body.get("place_and_route") or {}).get("metrics") or {}
        rows.append({
            "record": str(path.relative_to(ROOT)),
            "record_sha256": _sha256(path),
            "block": design.get("block"),
            "stages_completed": list(stages),
            "routed": routed,
            "target_clock_period_ns": body.get("target_clock_period_ns"),
            "status": body.get("status"),
            "closed": design.get("closed"),
            "closed_reason": design.get("closed_reason"),
            "setup_wns_ns": design.get("setup_wns_ns"),
            "hold_wns_ns": design.get("hold_wns_ns"),
            "post_route_fmax_hz": metrics.get("fmax_hz") or design.get("fmax_hz"),
            "core_area_um2": metrics.get("core_area_um2"),
            "standard_cell_area_um2": metrics.get("standard_cell_area_um2"),
            "macro_area_um2": metrics.get("macro_area_um2"),
            "signal_integrity_violations": design.get("signal_integrity_violations"),
        })

    routed_rows = [r for r in rows if r["routed"]]
    pre_layout = [r for r in rows if not r["routed"]]
    closed = [r for r in routed_rows if r["closed"] is True]
    not_closed = [r for r in routed_rows if r["closed"] is not True]
    blocks_closed = sorted({r["block"] for r in closed if r["block"]})
    report = {
        "schema": SCHEMA,
        "producer": {"tool": TOOL, "git": {"commit": _git("rev-parse", "HEAD")}},
        "view": arguments.view,
        "question": (
            "how much of this design is routed on ASAP7, and how much of what is "
            "routed closes?"
        ),
        "counts": {
            "records_read": len(rows),
            "routed_records": len(routed_rows),
            "routed_and_closed": len(closed),
            "routed_not_closed": len(not_closed),
            "pre_layout_only_records": len(pre_layout),
            "distinct_blocks_with_a_closed_routed_record": len(blocks_closed),
        },
        "blocks_with_a_closed_routed_record": blocks_closed,
        "closed_is_not_status": (
            "status is the verdict of the stages that ran; design.closed "
            "additionally requires the routed netlist to carry zero max-slew, "
            "max-cap and max-fanout violations. A record with POSITIVE setup and "
            "hold slack, zero DRC and zero antenna violations can still report "
            "closed=False -- measured on the half-depth compute unit for two "
            "max-slew violations, fixed by a 15% slew margin"
        ),
        "records": rows,
        "not_a_claim": [
            "ASAP7 is a predictive, non-manufacturable academic PDK; no row here is "
            "a silicon claim",
            "a pre-layout sta record is not a closure statement and is counted "
            "separately",
            "a closed block is not a closed chip: these are block-level runs, and "
            "what a full assembly costs is not measured here",
        ],
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report["counts"], indent=1, sort_keys=True))
    for row in sorted(not_closed, key=lambda r: str(r["record"]))[:12]:
        print(f"  NOT CLOSED {row['block']}: {str(row['closed_reason'])[:90]}")
    print(f"-> {arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
