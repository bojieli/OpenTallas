#!/usr/bin/env python3
"""The rungs the clock limiter does not cover, with what each one measured.

``tools/audit_asap7_fmax_inventory.py`` names the slowest ABI 3.0 block that has a
CLOSED routed record and calls it the design's clock limiter. That claim is honest
and incomplete in a specific way its own caveat states: a module with no closed
record is not on the list and could be slower. This reports exactly those -- the
modules some parent instantiates that no closed block contains -- together with
every NOT-MET routed measurement that exists for them.

Reading it. A module here with a measured fmax BELOW the limiter is a real rung:
the published clock does not cover it, and routing its parent would lower the
design's clock to that number. A module here with no measurement at all is
unmeasured, which is worse than a low number because nothing bounds it.

This is not a closure claim about anything. Every figure is read out of a record
some route wrote; nothing is estimated, and a not-met route is reported as not
met.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "opentallas.physical.asap7_uncovered_rungs.v1"
TOOL = "tools/audit_asap7_uncovered_rungs.py"
COVERAGE = ROOT / "results/physical_abi3/asap7/datapath_coverage.json"
INVENTORY = ROOT / "results/physical_abi3/asap7/frequency_inventory/asap7_fmax_inventory.json"
RECORDS = ROOT / "results/physical_abi3/asap7"


def _git_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT,
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results/physical_abi3/asap7/uncovered_rungs.json",
    )
    args = parser.parse_args()

    coverage = json.loads(COVERAGE.read_text())
    uncovered = {r["module"]: r for r in coverage["uncovered_and_instantiated"]}

    inventory = json.loads(INVENTORY.read_text())
    #: The inventory's own ``clock_limiter`` row, which is already filtered to the
    #: abi3 datapath family and excludes superseded modules. Taking the slowest
    #: entry of best_closed_fmax_per_block_slowest_first instead picks up retired
    #: blocks and probes -- it named ot_a3_vector_scale, a module replaced by
    #: ot_a3_vector_scale_pipe and instantiated by nothing.
    limiter = dict(inventory.get("clock_limiter") or {})
    limiter_mhz = (
        round(limiter["fmax_hz"] / 1e6, 1) if limiter.get("fmax_hz") else None
    )
    if limiter_mhz is not None:
        limiter["fmax_mhz"] = limiter_mhz

    #: Every routed record in the tree, by the top it was run on.
    measured: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(RECORDS.rglob("*.json")):
        try:
            record = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        design = record.get("design")
        if not isinstance(design, dict):
            continue
        top = design.get("top") or design.get("block")
        fmax = design.get("fmax_hz")
        if not top or not fmax:
            continue
        measured.setdefault(top, []).append(
            {
                "record": str(path.relative_to(ROOT)),
                "status": record.get("status"),
                "closed": design.get("closed"),
                "clock_period_ns": design.get("clock_period_ns"),
                "fmax_mhz": round(fmax / 1e6, 1),
                "cells": design.get("cells"),
                "area_um2": design.get("area_um2"),
            }
        )

    rows: list[dict[str, Any]] = []
    for name, row in uncovered.items():
        runs = sorted(measured.get(name, []), key=lambda r: r["fmax_mhz"])
        best = max((r["fmax_mhz"] for r in runs), default=None)
        rows.append(
            {
                "module": name,
                "instantiated_by": row["instantiated_by"],
                "best_measured_fmax_mhz": best,
                "below_the_limiter": (
                    None if best is None or limiter_mhz is None else best < limiter_mhz
                ),
                "runs": runs,
            }
        )
    #: Slowest measured first, then the unmeasured, because an unmeasured module
    #: bounds nothing at all.
    rows.sort(key=lambda r: (r["best_measured_fmax_mhz"] is None,
                             r["best_measured_fmax_mhz"] or 0))

    report = {
        "schema": SCHEMA,
        "producer": {"tool": TOOL, "git": {"commit": _git_commit()}},
        "derived_from": [
            str(COVERAGE.relative_to(ROOT)),
            str(INVENTORY.relative_to(ROOT)),
            "every routed record under results/physical_abi3/asap7",
        ],
        "limiter": limiter,
        "counts": {
            "uncovered_and_instantiated": len(rows),
            "measured": sum(1 for r in rows if r["best_measured_fmax_mhz"] is not None),
            "unmeasured": sum(1 for r in rows if r["best_measured_fmax_mhz"] is None),
            "measured_below_the_limiter": sum(1 for r in rows if r["below_the_limiter"]),
        },
        "rungs": rows,
        "not_a_claim": [
            "nothing here is a closure; a not-met route is reported as not met and "
            "its fmax is what the tool reported at that target, not a closing speed",
            "an fmax at a target is period-dependent when the worst path starts at "
            "an input port, because the SDC derives input delay as 20% of the clock "
            "period -- ot_a3_vector_compress_project is such a path",
            "a module with no measurement is UNMEASURED, which bounds the design's "
            "clock less than a low number does",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    print(f"limiter: {limiter.get('block')} at {limiter_mhz} MHz")
    print(f"{len(rows)} modules instantiated and not covered by it:")
    for row in rows:
        best = row["best_measured_fmax_mhz"]
        mark = "BELOW" if row["below_the_limiter"] else ("     " if best else "unmeasured")
        print(f"  {mark:10} {str(best or '-'):>7} MHz  {row['module']:42}"
              f" <- {', '.join(row['instantiated_by']) or 'nothing'}")
    print(f"-> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
