#!/usr/bin/env python3
"""Measure an engine's per-lane throughput on two independent simulators.

The cycle model's ``engine.<family>.work_per_lane_cycle`` is a rate: how much
of the work its family counts one engine instance retires per clock.  Every
one of them was a hand-written assumption.  For the tensor and vector families
an executed Qwen operator campaign already measures it as a side effect; for
the reduction family -- whose endpoint has a full place-and-route result in
*both* physical views -- nothing did, so this campaign measures it directly.

The measurement is deliberately narrow.  It drives the endpoint back to back
with the downstream always ready and counts flits accepted against clocks
elapsed.  That is an upper bound on the rate, which is the honest direction:
it is what the engine can do when nothing is in its way, and the cycle model
charges contention separately.

Two simulators run the same bench and must produce the same counts.  A rate
one simulator produces is a property of that simulator until a second one
agrees.

Usage::

    PYTHONPATH=. python3 tools/run_abi3_engine_rate_campaign.py \\
        --output results/rtl/abi3_engine_rate.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from runtime.abi3.capability import canonical_json  # noqa: E402

SCHEMA = "opentallas.abi3.engine_rate.v1"

PINNED_VERILATOR = Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"

CASES: tuple[dict[str, Any], ...] = (
    {
        "name": "reduction_endpoint_s8_g2",
        "engine_family": "reduction",
        "top": "tb_ot_reduction_endpoint_rate",
        "sources": ["rtl/ot_reduction_tree.sv", "rtl/test/tb_ot_reduction_endpoint_rate.sv"],
        "work_counter": "reduction.elements",
        "design": "ot_reduction_endpoint",
        "routed_in": [
            "results/physical_abi3/sky130hd/reduction_s8_g2/pnr.json",
            "results/physical_abi3/asap7/reduction_s8_g2/pnr.json",
        ],
    },
)

CLAIM_BOUNDARY = [
    "A rate measured with the downstream always ready is what the engine can "
    "do unobstructed.  It is an upper bound, not an achieved service rate.",
    "The bench drives the endpoint's own valid/ready interface; the memory, "
    "fabric and arbitration that would feed it in a machine are not present.",
    "This measures one engine instance.  How many instances a machine has is "
    "a capability claim no run here supports.",
    "A cycle count is not a time.  It becomes a time only under a clock, and "
    "the clock belongs to a place-and-route result.",
]

RESULT_RE = re.compile(
    r"PASS: reduction endpoint SOURCES=(?P<sources>\d+) GROUPS=(?P<groups>\d+) "
    r"flits=(?P<flits>\d+) results=(?P<results>\d+) cycles=(?P<cycles>\d+) "
    r"elements_per_cycle=(?P<rate>[0-9.]+)"
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(cmd: list[str], cwd: Path, timeout: int = 1800) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout
    )


def parse(output: str) -> dict[str, int]:
    match = RESULT_RE.search(output)
    if not match:
        raise SystemExit(f"bench produced no parsable PASS line:\n{output}")
    body = match.groupdict()
    return {
        "sources": int(body["sources"]),
        "groups": int(body["groups"]),
        "flits": int(body["flits"]),
        "results": int(body["results"]),
        "cycles": int(body["cycles"]),
    }


def run_iverilog(case: dict[str, Any], work: Path) -> dict[str, Any]:
    binary = work / "iverilog.vvp"
    build = run(
        ["iverilog", "-g2012", "-o", str(binary), "-s", case["top"]]
        + [str(REPO / s) for s in case["sources"]],
        cwd=work,
    )
    if build.returncode != 0:
        raise SystemExit(f"iverilog build failed:\n{build.stdout}{build.stderr}")
    completed = run([str(binary)], cwd=work)
    if completed.returncode != 0:
        raise SystemExit(f"iverilog run failed:\n{completed.stdout}{completed.stderr}")
    counts = parse(completed.stdout)
    version = run(["iverilog", "-V"], cwd=work).stdout.splitlines()[0].strip()
    return {"simulator": "iverilog", "version": version, **counts}


def run_verilator(case: dict[str, Any], work: Path) -> dict[str, Any]:
    binary_name = "rate_vl"
    executable = str(PINNED_VERILATOR) if PINNED_VERILATOR.exists() else "verilator"
    obj = work / "obj_verilator"
    build = run(
        [
            executable, "--binary", "--timing", "-Wno-fatal",
            "--top-module", case["top"], "-Mdir", str(obj),
        ]
        + [str(REPO / s) for s in case["sources"]]
        + ["-o", binary_name],
        cwd=work,
    )
    if build.returncode != 0:
        raise SystemExit(f"verilator build failed:\n{build.stdout}{build.stderr}")
    completed = run([str(obj / binary_name)], cwd=work)
    if completed.returncode != 0:
        raise SystemExit(f"verilator run failed:\n{completed.stdout}{completed.stderr}")
    counts = parse(completed.stdout)
    version = run([executable, "--version"], cwd=work).stdout.strip()
    return {"simulator": "verilator", "version": version, **counts}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    if args.output.exists() and not args.force:
        raise SystemExit(f"{args.output} already exists; pass --force to overwrite")
    if shutil.which("iverilog") is None:
        raise SystemExit("iverilog is not installed; this campaign needs two simulators")

    cases: list[dict[str, Any]] = []
    for case in CASES:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            runs = [run_iverilog(case, work), run_verilator(case, work)]
        keys = ("flits", "results", "cycles", "sources", "groups")
        agree = all(
            runs[0][key] == runs[1][key] for key in keys
        )
        if not agree:
            raise SystemExit(
                f"the two simulators disagree on {case['name']}: {runs}"
            )
        flits = runs[0]["flits"]
        cycles = runs[0]["cycles"]
        cases.append(
            {
                "name": case["name"],
                "engine_family": case["engine_family"],
                "design": case["design"],
                "work_counter": case["work_counter"],
                "work_units": flits,
                "cycles": cycles,
                "work_per_lane_cycle": flits / cycles,
                "simulators_agree": True,
                "runs": runs,
                "routed_in": case["routed_in"],
                "sources": {
                    str(s): sha256_file(REPO / s) for s in case["sources"]
                },
                "note": (
                    f"{flits} flits accepted in {cycles} clocks with the "
                    "downstream always ready; the trailing clocks are the last "
                    "group draining, so the steady-state rate is the limit this "
                    "figure approaches from below."
                ),
            }
        )

    body = {
        "schema": SCHEMA,
        "cases": cases,
        "status": "pass",
        "claim_boundary": CLAIM_BOUNDARY,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json(body))
    print(f"wrote {args.output}")
    for case in cases:
        print(
            f"  {case['name']:28s} {case['work_units']:>8d} {case['work_counter']} "
            f"in {case['cycles']:>8d} cycles = "
            f"{case['work_per_lane_cycle']:.6f} work/lane/cycle "
            f"(two simulators agree)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
