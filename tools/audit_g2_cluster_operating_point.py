#!/usr/bin/env python3
"""Neither knob closes the G2 cluster: not the clock, and not utilisation.

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

#: The other axis.  Period was the wrong knob, so the shipping configuration
#: was re-run at lower utilisation -- the knob that changes the placement
#: density repeaters have to work in.  It does not close either.
#:
#: These are NOT a clean single-variable comparison against the period points
#: above, and saying so matters: the utilisation runs also carry the
#: performance knobs (CRC_CACHE=1, FAST_FRONT_END=1) and 2,884,444 instances
#: against 2,442,446, so utilisation and logic content moved together.  What
#: they establish is weaker and still useful: at 4.75 ns the cluster does not
#: close at util 25 or at util 20, and the failure is max-slew in both.
UTILISATION_POINTS = (
    {
        "core_utilization": 20,
        "clock_period_ns": 4.75,
        "fmax_mhz": 272.0,
        "hold_violations": 0,
        "max_slew_violations": 20,
        "max_cap_violations": 0,
        "instance_count": 2_884_444,
        "closed": False,
        "performance_knobs": {"CRC_CACHE": 1, "FAST_FRONT_END": 1},
        "git_commit": "2bb16488",
        "worktree_dirty": False,
        "source_root": "/home/ubuntu/ot-ship2",
    },
    {
        "core_utilization": 30,
        "clock_period_ns": 4.75,
        "fmax_mhz": 280.9,
        "hold_violations": 0,
        "max_slew_violations": 5,
        "max_cap_violations": 0,
        "max_fanout_violations": 0,
        "drc_errors": 0,
        "setup_wns_ns": 1.18987,
        "instance_count": 2_216_811,
        "achieved_utilization_fraction": 0.320953,
        "closed": False,
        "closed_reason": (
            "signal-integrity violations in the routed netlist: "
            "max_slew_violations 5"
        ),
        "performance_knobs": {"CRC_CACHE": 1, "FAST_FRONT_END": 1},
        "git_commit": "2bb16488",
        "worktree_dirty": False,
        "source_root": "/home/ubuntu/ot-ship2",
    },
    {
        "core_utilization": 35,
        "clock_period_ns": 4.75,
        "fmax_mhz": 260.0,
        "hold_violations": 0,
        "max_slew_violations": 3,
        "max_cap_violations": 0,
        "instance_count": 2_027_815,
        "achieved_utilization_fraction": 0.372705,
        "closed": False,
        "closed_reason": (
            "signal-integrity violations in the routed netlist: "
            "max_slew_violations 3"
        ),
        "performance_knobs": {"CRC_CACHE": 1, "FAST_FRONT_END": 1},
        "git_commit": "2bb16488",
        "worktree_dirty": False,
        "source_root": "/home/ubuntu/ot-ship2",
    },
    {
        "core_utilization": 40,
        "clock_period_ns": 4.75,
        "fmax_mhz": 286.1,
        "hold_violations": 20,
        "max_slew_violations": 12,
        "max_cap_violations": 0,
        "instance_count": 1_875_402,
        "achieved_utilization_fraction": 0.423527,
        "closed": False,
        "closed_reason": (
            "signal-integrity violations in the routed netlist: "
            "max_slew_violations 12; and the first hold failures of the "
            "sweep, hold_violations 20"
        ),
        "performance_knobs": {"CRC_CACHE": 1, "FAST_FRONT_END": 1},
        "git_commit": "2bb16488",
        "worktree_dirty": False,
        "source_root": "/home/ubuntu/ot-ship2",
    },
)


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
        "utilisation_points_measured": list(UTILISATION_POINTS),
        "utilisation_reading": (
            "the sweep is now four same-build points (2bb16488, "
            "/home/ubuntu/ot-ship2) and it does NOT describe a gradient.  "
            "Max-slew violations by utilisation: 20 at util 20, 5 at util 30, "
            "3 at util 35, 12 at util 40.  Slew has a MINIMUM near util 35 "
            "and worsens past it.  Util 40 also produces hold_violations 20 "
            "-- the first hold failures anywhere in this sweep -- so packing "
            "the core past the mid-thirties trades a signal-integrity "
            "problem for a timing one.  Instance count is the only quantity "
            "monotone across all four: 2,884,444, 2,216,811, 2,027,815, "
            "1,875,402.  fmax is not even unimodal: 272.0, 280.9, 260.0, "
            "286.1 MHz.  "
            "This reading has now been rewritten three times by successive "
            "points, and the sequence is the finding.  Two points said "
            "lowering utilisation makes slew worse, so the knob should be "
            "raised.  A third kept slew falling but broke the claim that "
            "fmax rose with it.  A fourth broke the slew trend itself and "
            "introduced a failing check that the previous three had reported "
            "as clean at every point.  Each intermediate reading was a "
            "monotone story fitted to the points then in hand, and each was "
            "falsified by the next measurement.  What survives is the "
            "shape -- a slew optimum around util 30-35 at 3-5 violations, "
            "bounded above and below by worse -- and the fact that NO point "
            "measured closes at 4.75 ns.  "
            "The util-25 point (12 violations, 2,442,446 instances, 274.1 "
            "MHz) sits at 58ce25bb out of /home/ubuntu/ot-phys, a different "
            "commit and source root, so it is corroboration and not a fifth "
            "point of this series.  "
            "max-cap is 0 at all four points, and DRC and antenna are 0 at "
            "util 30, 35 and 40.  The remaining question is not which "
            "utilisation closes the design -- none of the four does -- but "
            "whether the slew constraint itself is the right one, which is "
            "where this audit said the question would move if the sweep "
            "failed.  It has failed; the question has moved"
        ),
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
            "utilisation was the remaining candidate and util 20 has now been "
            "measured: it does not close.  util 30 is the last point of that "
            "sweep.  If it also fails, the cluster does not close at 4.75 ns "
            "under either knob, and the next question is the slew constraint "
            "itself rather than the placement"
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
