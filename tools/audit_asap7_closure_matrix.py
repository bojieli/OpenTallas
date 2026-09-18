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


def _why_not_closed(body: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
    """Separate a DESIGN failure from a FLOW artifact, from the record's own fields.

    ``design.closed`` is left exactly as recorded.  What this adds is the reason,
    because three of them are not the same reason:

    * ``routed_netlist_dirty`` -- the routed netlist really does carry max-slew,
      max-cap or max-fanout violations.  A design problem, or a slew-margin knob.
    * ``routed_timing_not_met`` -- the post-route netlist misses setup or hold.
    * ``blocked_only_by_a_pre_layout_stage`` -- the routed netlist is clean AND meets
      setup and hold post-route, and the only failing acceptance stage is a
      PRE-LAYOUT one, on an unrepaired netlist with an ideal clock.  That is a
      property of which stages were asked for, not of the design: the same RTL run
      with ``--stages pnr`` alone has nothing to fail.
    * ``signal_integrity_fields_absent`` -- an old record that predates the fields,
      so closure can be neither asserted nor denied without a re-route.
    """
    si = {
        key: metrics.get(key)
        for key in ("max_slew_violations", "max_cap_violations", "max_fanout_violations")
    }
    if any(value is None for value in si.values()):
        return {"class": "signal_integrity_fields_absent", "signal_integrity": si}

    dirty = {key: value for key, value in si.items() if value}
    physical = {
        "drc_errors": metrics.get("drc_errors"),
        "antenna_violating_nets": metrics.get("antenna_violating_nets"),
    }
    setup_violations = metrics.get("setup_violations")
    hold_violations = metrics.get("hold_violations")

    if dirty:
        return {
            "class": "routed_netlist_dirty",
            "signal_integrity": si,
            "violating": dirty,
        }
    if setup_violations or hold_violations:
        return {
            "class": "routed_timing_not_met",
            "setup_violations": setup_violations,
            "hold_violations": hold_violations,
        }
    if any(physical.values()):
        return {"class": "routed_physically_dirty", "physical": physical}

    failing_pre_layout = [
        check.get("stage")
        for check in (body.get("acceptance") or {}).get("checks") or ()
        if isinstance(check, dict)
        and check.get("met") is False
        and "pre-layout" in str(check.get("scope", ""))
    ]
    if failing_pre_layout:
        return {
            "class": "blocked_only_by_a_pre_layout_stage",
            "failing_pre_layout_stages": failing_pre_layout,
            "note": (
                "the routed netlist is clean and meets setup and hold; the "
                "not-closed verdict comes from a pre-layout, ideal-clock stage that "
                "ran alongside it.  Re-running with --stages pnr alone removes the "
                "stage, not a violation"
            ),
        }
    return {"class": "unclassified", "signal_integrity": si}


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
            "why_not_closed": (
                None
                if design.get("closed") is True or not routed
                else _why_not_closed(body, metrics)
            ),
        })

    def _reason_counts(records: list[dict[str, Any]]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for record in records:
            name = (record.get("why_not_closed") or {}).get("class", "unknown")
            counts[name] = counts.get(name, 0) + 1
        return dict(sorted(counts.items()))

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
        "why_the_not_closed_records_are_not_closed": _reason_counts(not_closed),
        "recoverable_by_dropping_a_pre_layout_stage": sorted(
            {
                r["block"]
                for r in not_closed
                if (r.get("why_not_closed") or {}).get("class")
                == "blocked_only_by_a_pre_layout_stage"
                and r["block"]
            }
        ),
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
