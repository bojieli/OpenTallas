#!/usr/bin/env python3
"""The ABI 3.0 vector set, replayed at both dependence-check depths.

``results/derived/abi3_iso_area_three_level_audit.json`` measures ONE
combinational cone as the control plane's clock -- the dependence table's
128-range conflict check -- and names splitting it as the highest-leverage change
available, sized at 2.00x sustained throughput (device-level 1.075x -> 2.152x of
an A100) at zero datapath area.  ``ot_a3_dependence_table`` takes ``CHECK_STAGES``
and ``rtl/test/tb_a3_dependence_table_depth.sv`` already proves depth 2 equals
depth 1 delayed by one cycle, over 20,000 cycles, under both simulators.

What that does NOT prove is that the CONSUMER is right.  ``ot_a3_microsequencer``
reads the conflict in the state after it raises ``checkN_valid``; at depth 2 the
answer is a cycle later, and its hazard scan is pipelined -- each cycle issues a
check pair and folds in the previous cycle's results -- so the last pair's answer
arrives after the loop has already left.  Dropping it would issue an instruction
over a live hazard, which is a silent wrong answer rather than a stall.

So this replays the whole committed vector set through the real control plane at
``DEP_CHECK_STAGES`` 1 and 2 and requires BOTH to print the marker the vector set
derives from its golden execution on ``runtime.sim.device.Device`` -- the same
programs, the same program headers, the same engine-issue events, the same traps.
A depth that reordered or dropped anything cannot print it.

Both simulators run both depths, because they disagree about SystemVerilog in ways
that have mattered here: indexing a part-select is accepted by one and rejected by
the other, which is why the owed-cycle count is written as a comparison.

    PYTHONPATH=. python3 tools/rtl_abi3_dep_check_depth_campaign.py \\
        --output results/rtl/a3_dep_check_depth_campaign.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.rtl_abi3_campaign import (  # noqa: E402
    PINNED_VERILATOR_VERSION,
    RTL_SOURCES,
    TOOLS_ROOT,
    VECTOR_DIR,
    VECTOR_FILES,
    resolve,
    simulator_case,
)

SCHEMA = "opentallas.a3_dep_check_depth.v1"
DEPTHS = (1, 2)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=REPO / "results/rtl/a3_dep_check_depth_campaign.json"
    )
    parser.add_argument("--build-dir", type=Path, default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.output.exists() and not args.force:
        raise SystemExit(f"refusing to overwrite {args.output}; pass --force")

    vectors = json.loads((VECTOR_DIR / "abi3_rtl_vectors.json").read_text())
    marker = vectors["required_marker"]
    executables = {
        "iverilog": resolve("iverilog", None),
        "vvp": resolve("vvp", None),
        "verilator": resolve(
            "verilator", TOOLS_ROOT / f"verilator-{PINNED_VERILATOR_VERSION}/bin/verilator"
        ),
    }

    root = args.build_dir or (REPO / "rtl/build/dep_check_depth")
    rtl = [str(REPO / path) for path in RTL_SOURCES]
    by_depth: dict[str, Any] = {}
    for depth in DEPTHS:
        build = root / f"depth{depth}"
        build.mkdir(parents=True, exist_ok=True)
        for name in VECTOR_FILES:
            shutil.copy2(VECTOR_DIR / name, build / name)
        iverilog_compile = [
            str(executables["iverilog"]), "-g2012",
            # Icarus sets a top parameter by hierarchical path.
            "-P", f"tb_a3_microsequencer.dut.DEP_CHECK_STAGES={depth}",
            "-s", "tb_a3_microsequencer", "-o", "a3_sim.vvp",
            *rtl,
            str(REPO / "rtl/test/a3_microsequencer_top.sv"),
            str(REPO / "rtl/test/tb_a3_microsequencer.sv"),
        ]
        verilator_compile = [
            str(executables["verilator"]), "--cc", "--exe", "--build",
            "-Wall", "-Wno-fatal", "-Wno-DECLFILENAME",
            f"-GDEP_CHECK_STAGES={depth}",
            "--top-module", "ot_a3_microsequencer_top", "--Mdir", "obj_a3",
            *rtl,
            str(REPO / "rtl/test/a3_microsequencer_top.sv"),
            str(REPO / "rtl/test/a3_microsequencer_harness.cpp"),
            "-CFLAGS", "-std=c++17",
        ]
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(
                    simulator_case, "iverilog", iverilog_compile,
                    [str(executables["vvp"]), "a3_sim.vvp"], build, marker,
                ),
                pool.submit(
                    simulator_case, "verilator", verilator_compile,
                    ["./obj_a3/Vot_a3_microsequencer_top"], build, marker,
                ),
            ]
            cases = [f.result() for f in futures]
        by_depth[str(depth)] = {
            case["name"]: {
                "status": case["status"],
                "marker_present": case["marker_present"],
                "compile_returncode": case["compile_returncode"],
                "run_returncode": case["run_returncode"],
                "log_sha256": case["log_sha256"],
                "compile_tail": case["compile_log"][-1200:],
                "run_tail": case["run_log"][-1200:],
            }
            for case in cases
        }
        print(
            f"depth {depth}: "
            + ", ".join(f"{c['name']}={c['status']}" for c in cases),
            flush=True,
        )

    passed = all(
        row["status"] == "pass"
        for depth in by_depth.values()
        for row in depth.values()
    )
    report = {
        "schema": SCHEMA,
        "question": (
            "does the real control plane replay the whole ABI 3.0 vector set "
            "identically with the dependence table's conflict reduction split "
            "across two cycles?"
        ),
        "required_marker": marker,
        "marker_is": (
            "derived from the vector set's golden execution on "
            "runtime.sim.device.Device: the number of programs, program headers, "
            "engine-issue events and traps that had to be reproduced"
        ),
        "depths": by_depth,
        "status": "pass" if passed else "fail",
        "what_a_pass_means": (
            "both depths reproduce the same programs, the same engine-issue "
            "events and the same traps.  The deeper one takes more cycles to do "
            "it, which is the whole point: the cycle buys the clock."
        ),
        "not_a_claim": [
            "no frequency is claimed here; the routed record is separate evidence",
            "this is the vector set, not a shipped model's token",
        ],
        "tools": executables,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=1, sort_keys=True, default=str) + "\n")
    print(f"{report['status']} -> {args.output}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
