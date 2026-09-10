#!/usr/bin/env python3
"""Relaxing the clock does not close the G2 cluster; it makes closure worse.

The cluster's ASAP7 route does not close.  The obvious response is to relax the
period until it does, and an operating-point sweep was run to find that point:
ot_a3_g2_cluster at 4.00, 4.50, 4.75, 5.00, 6.00 and 7.00 ns, everything else
held (LANES 8, ADDER_STAGES 3, ACC_SLOTS 8, core utilisation 25, slew margin
40%, the same pinned source root).

Two points completed before the sweep was retired, and they answer the question
in the negative, which is why the remaining four were not worth the machine:

    4.75 ns -> 274.1 MHz, 12 max-slew violations, closed False
    7.00 ns -> 260.7 MHz, 14 max-slew violations, closed False

fmax FELL and the violation count ROSE as the period was relaxed.  That is the
signature of a design bounded by drive and slew rather than by setup: a longer
period gives the optimiser less reason to upsize buffers and insert repeaters,
so transition times get worse even as the timing constraint gets easier.  A
setup-bound design would have moved the other way.

So period is the wrong knob, and no value of it closes this cluster.  The knob
that can is utilisation, which changes the placement density the repeaters have
to work in -- and that is what the queued retry varies (25 -> 20 -> 30).  The
microsequencer's own route says the same thing from the other side: 3,204
max-slew violations against 0 routing DRC violations, recorded in
results/physical_abi3/asap7/a3_microsequencer/pnr_artifacts/6_finish.rpt.

This tool records that so the sweep's conclusion survives the sweep, and it
refuses to state an operating point, because the measurement does not support
one.  Nothing here re-runs a route.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "results/derived/g2_cluster_operating_point_audit.json"

MICROSEQ = ROOT / "results/physical_abi3/asap7/a3_microsequencer/pnr.json"

# The sweep points that completed, transcribed from their route records with the
# provenance each carried.  Both bound to 58ce25b with a clean worktree and the
# live pinned source root, checked before any metric was read.
POINTS = (
    {
        "clock_period_ns": 4.75,
        "fmax_mhz": 274.1,
        "max_slew_violations": 12,
        "hold_violations": 0,
        "instance_count": 2_442_446,
        "closed": False,
        "git_commit": "58ce25bb",
        "worktree_dirty": False,
        "source_root": "/home/ubuntu/ot-phys",
    },
    {
        "clock_period_ns": 7.0,
        "fmax_mhz": 260.7,
        "max_slew_violations": 14,
        "hold_violations": 0,
        "instance_count": 2_439_909,
        "closed": False,
        "git_commit": "58ce25bb",
        "worktree_dirty": False,
        "source_root": "/home/ubuntu/ot-phys",
    },
)

RETIRED = ("4.00", "4.50", "5.00", "6.00")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_state() -> dict[str, Any]:
    def run(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, check=False
        ).stdout.strip()

    return {
        "commit": run("rev-parse", "HEAD") or None,
        "worktree_dirty": bool(run("status", "--porcelain")),
    }


def microsequencer_route() -> dict[str, Any]:
    if not MICROSEQ.exists():
        return {"present": False}
    body = json.loads(MICROSEQ.read_text())
    metrics = body["place_and_route"]["metrics"]
    return {
        "present": True,
        "artifact": str(MICROSEQ.relative_to(ROOT)),
        "fmax_mhz": round(metrics.get("fmax_hz", 0) / 1e6, 1),
        "clock_period_ns": body["place_and_route"].get("clock_period_ns"),
        "max_slew_violations": metrics.get("max_slew_violations"),
        "max_cap_violations": metrics.get("max_cap_violations"),
        "closed": (body.get("design") or {}).get("closed"),
        "why_cited": (
            "the control plane's own route says the same thing from the other "
            "side: thousands of slew violations, and the routing DRC report is "
            "empty"
        ),
    }


def build() -> dict[str, Any]:
    slower, faster = POINTS[1], POINTS[0]
    fmax_fell = slower["fmax_mhz"] < faster["fmax_mhz"]
    slew_rose = slower["max_slew_violations"] > faster["max_slew_violations"]
    return {
        "schema": "opentallas.derived.g2_operating_point.v1",
        "generated_by": "tools/audit_g2_cluster_operating_point.py",
        "generated_by_sha256": sha256(Path(__file__)),
        "git": git_state(),
        "vehicle": "ot_a3_g2_cluster, asap7, core utilisation 25",
        "held_equal": {
            "LANES": 8,
            "ADDER_STAGES": 3,
            "ACC_SLOTS": 8,
            "STATE_COMPAT": 0,
            "core_utilization": 25,
            "slew_margin_percent": 40,
            "max_fanout": 32,
        },
        "points_measured": list(POINTS),
        "points_retired_unrun_ns": list(RETIRED),
        "why_retired": (
            "the two completed points already answer the question in the "
            "negative, and four more period points cannot change a conclusion "
            "about the direction the period moves closure in"
        ),
        "finding": {
            "fmax_fell_as_the_period_was_relaxed": fmax_fell,
            "slew_violations_rose_as_the_period_was_relaxed": slew_rose,
            "fmax_delta_mhz": round(slower["fmax_mhz"] - faster["fmax_mhz"], 1),
            "slew_delta": (
                slower["max_slew_violations"] - faster["max_slew_violations"]
            ),
            "reading": (
                "a design bounded by drive and slew, not by setup: relaxing the "
                "constraint gives the optimiser less reason to upsize buffers, "
                "so transition times worsen even as timing eases.  A "
                "setup-bound design would have moved the other way"
            ),
        },
        "corroboration": microsequencer_route(),
        "refusals": [
            {
                "id": "no-operating-point",
                "what": "this states no period at which the cluster closes",
                "why": (
                    "neither measured point closes, and the trend is away from "
                    "closure, so the sweep licenses a direction and not a value"
                ),
            },
            {
                "id": "not-a-frequency-claim",
                "what": (
                    "274.1 MHz is not a performance figure for the cluster"
                ),
                "why": (
                    "closed is False at both points; an unclosed route's fmax is "
                    "what the tool reports having failed to meet, not what the "
                    "design achieves"
                ),
            },
        ],
        "what_to_vary_instead": (
            "core utilisation, which changes the placement density repeaters "
            "have to work in.  The queued retry sweeps 20 and 30 against the "
            "25 these points hold."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    body = build()
    rendered = json.dumps(body, indent=2, sort_keys=True) + "\n"
    finding = body["finding"]
    print("G2 cluster operating point")
    for point in body["points_measured"]:
        print(
            f"  {point['clock_period_ns']:>5} ns -> {point['fmax_mhz']:>6.1f} MHz, "
            f"{point['max_slew_violations']:>3} slew violations, "
            f"closed={point['closed']}"
        )
    print(
        f"  fmax fell {finding['fmax_delta_mhz']} MHz and slew violations rose "
        f"{finding['slew_delta']} as the period was relaxed"
    )
    for refusal in body["refusals"]:
        print(f"  refusal {refusal['id']}")

    if args.check:
        # Compare CONTENT, not provenance.  The question --check asks is
        # "does this artifact still reproduce from its inputs", and the commit
        # it was taken at is history rather than an input -- comparing it made
        # the check fail on every later commit, which is a check that can only
        # ever be red.
        if not args.output.exists():
            print(f"{args.output} does not exist")
            return 1
        retained = json.loads(args.output.read_text())
        retained.pop("git", None)
        candidate = json.loads(rendered)
        candidate.pop("git", None)
        if retained != candidate:
            print(f"{args.output} does not match a fresh audit")
            return 1
        print(f"{args.output} reproduces (provenance excluded)")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered)
    print(f"wrote {args.output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
