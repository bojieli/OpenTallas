#!/usr/bin/env python3
"""Rank every ASAP7 record by measured Fmax, and name the block that gates the clock.

``results/physical_abi3/asap7/frequency_inventory/asap7_fmax_inventory.json`` was
written by hand -- it carries no ``producer`` -- and it went stale: at 130 records it
ranked ``ot_a3_lq8`` at 140.3 MHz from a LOOSE 16 ns route while the same block has a
closed 2.0 ns record at 512.8 MHz.  A frequency ranking that reads a block's loose
route as its ceiling will name the wrong limiter, and the whole-design operating
point is exactly what the ranking is used for.  So this regenerates it from the
records, and adds the reduction the ad-hoc file left to the reader.

**Fmax against target.**  A routed record's ``fmax_hz`` is what THAT route achieved
at THAT target.  It is not the block's ceiling: a block routed at 16 ns has had no
reason to be fast, and the number says so.  The per-block figure this reports is
therefore the best fmax over the block's CLOSED routed records, and the target it
came from is reported beside it, so a loose-target number cannot pass as a limit.

**The limiter.**  The design's clock cannot exceed the slowest block on it, so the
ranking's bottom row is the operating point and everything above it has headroom.
That single row is what an iso-area or TPOT claim rests on, which is why it is
computed here rather than eyeballed.
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
SCHEMA = "opentallas.physical.asap7_fmax_inventory.v2"
TOOL = "tools/audit_asap7_fmax_inventory.py"


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--view", default="asap7")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results/physical_abi3/asap7/frequency_inventory/asap7_fmax_inventory.json",
    )
    arguments = parser.parse_args(argv)

    base = ROOT / "results/physical_abi3" / arguments.view
    records: list[dict[str, Any]] = []
    for path in sorted(base.rglob("*.json")):
        if "artifacts" in path.parts or "frequency_inventory" in path.parts:
            continue
        try:
            body = json.loads(path.read_text())
        except ValueError:
            continue
        design = body.get("design")
        if not isinstance(design, dict):
            continue
        stages = tuple(body.get("stages_completed") or ())
        post_route = "pnr" in stages or "place_and_route" in stages
        metrics = (body.get("place_and_route") or {}).get("metrics") or {}
        integrity = (body.get("place_and_route") or {}).get(
            "signal_integrity_constraints"
        ) or {}
        target = body.get("target_clock_period_ns")
        fmax = metrics.get("fmax_hz") or design.get("fmax_hz")
        setup_wns = metrics.get("setup_wns_ns", design.get("setup_wns_ns"))
        headroom = None
        if target and setup_wns is not None:
            # How much of the target the route did NOT need.  A large headroom means
            # the target was loose and the fmax is not a limit.
            headroom = float(setup_wns) / float(target)
        records.append(
            {
                "record": str(path.relative_to(ROOT)),
                "record_sha256": _sha256(path),
                "block": design.get("block"),
                "post_route": post_route,
                "stages": list(stages),
                "closed": design.get("closed"),
                "target_clock_period_ns": target,
                "fmax_hz": fmax,
                "setup_wns_ns": setup_wns,
                "target_headroom": headroom,
                "slew_margin_percent": integrity.get("slew_margin_percent"),
                "max_slew_violations": metrics.get("max_slew_violations"),
                "max_cap_violations": metrics.get("max_cap_violations"),
                "max_fanout_violations": metrics.get("max_fanout_violations"),
                "drc_errors": metrics.get("drc_errors"),
                "antenna_violating_nets": metrics.get("antenna_violating_nets"),
                "standard_cell_area_um2": metrics.get("standard_cell_area_um2"),
                "purpose": body.get("purpose"),
            }
        )

    routed = [r for r in records if r["post_route"]]
    closed = [r for r in routed if r["closed"] is True and r["fmax_hz"]]

    per_block: dict[str, dict[str, Any]] = {}
    for record in closed:
        block = record["block"]
        if not block:
            continue
        current = per_block.get(block)
        if current is None or float(record["fmax_hz"]) > float(current["fmax_hz"]):
            per_block[block] = {
                "block": block,
                "fmax_hz": record["fmax_hz"],
                "at_target_clock_period_ns": record["target_clock_period_ns"],
                "target_headroom": record["target_headroom"],
                "slew_margin_percent": record["slew_margin_percent"],
                "standard_cell_area_um2": record["standard_cell_area_um2"],
                "record": record["record"],
            }

    ranking = sorted(per_block.values(), key=lambda entry: float(entry["fmax_hz"]))
    limiter = ranking[0] if ranking else None

    report = {
        "schema": SCHEMA,
        "producer": {"tool": TOOL, "git": {"commit": _git("rev-parse", "HEAD")}},
        "view": arguments.view,
        "inventory_of": f"results/physical_abi3/{arguments.view}/**",
        "basis": (
            "Every field is copied from a record a run wrote: design.fmax_hz (ORFS "
            "finish__timing__fmax for a routed record, OpenSTA 1/(period - WNS) for a "
            "pre-layout one), design.closed and the signal-integrity counts that "
            "decide it, and target_clock_period_ns.  target_headroom is setup WNS "
            "over the target: a large value means the target was loose and the fmax "
            "is what that route achieved, NOT the block's ceiling."
        ),
        "counts": {
            "record_count": len(records),
            "post_route_record_count": len(routed),
            "closed_routed_record_count": len(closed),
            "distinct_blocks_with_a_closed_routed_record": len(per_block),
        },
        "best_closed_fmax_per_block_slowest_first": ranking,
        "clock_limiter": (
            None
            if limiter is None
            else {
                **limiter,
                "note": (
                    "the design's clock cannot exceed the slowest block on it, so this "
                    "row is the whole-design operating point and every block above it "
                    "has headroom"
                ),
            }
        ),
        "records": records,
        "not_a_claim": [
            "ASAP7 is a predictive, non-manufacturable academic PDK; no row here is a "
            "silicon claim",
            "a block's best closed fmax is the best over the routes that were RUN, not "
            "a proven ceiling: a block nobody routed at a tight target will read slow",
            "the limiter is the slowest block that has a closed record.  A block with "
            "no closed record at all is not on this list and could be slower",
        ],
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report["counts"], indent=1, sort_keys=True))
    print("\nbest closed fmax per block, slowest first:")
    for entry in ranking:
        print(
            f"  {float(entry['fmax_hz'])/1e6:9.1f} MHz  T={entry['at_target_clock_period_ns']!s:>6} ns "
            f" headroom={entry['target_headroom'] if entry['target_headroom'] is None else round(entry['target_headroom'],3)!s:>6}"
            f"  {entry['block']}"
        )
    if limiter:
        print(
            f"\nclock limiter: {limiter['block']} at {float(limiter['fmax_hz'])/1e6:.1f} MHz "
            f"({limiter['record']})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
