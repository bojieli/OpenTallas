#!/usr/bin/env python3
"""Both depths of the dependence table's conflict check, under both simulators.

``results/derived/abi3_iso_area_three_level_audit.json`` measures one
combinational cone as the control plane's clock: the dependence table's
128-range conflict check, 128 sixteen-bit equalities and 256 forty-bit interval
compares OR-ed together, at a 16.10 ns pre-layout critical path.  That audit
names splitting the path as the highest-leverage change available to this design
and sizes it at 2.00x sustained throughput -- L3 1.075x -> 2.152x of an A100 --
at zero datapath area, while refusing to call the 2.00x a result until a closed
routed record exists at 534 MHz or better.

``ot_a3_dependence_table`` now takes ``CHECK_STAGES``.  This campaign is the
claim that the parameter costs nothing at its default and means what it says at
2, which has to hold before any frequency number from it is worth having.

Three instances are driven by one stimulus stream: the module as committed before
the parameter existed, the new module at ``CHECK_STAGES = 1``, and the new module
at ``CHECK_STAGES = 2``.

* the reference and depth 1 must agree on EVERY cycle, including
  ``dbg_ranges_used`` -- that is the claim that the default is the netlist it
  always was, and it is what lets the deeper form be adopted by one consumer at a
  time rather than all at once;
* depth 2 must equal the reference delayed by exactly one cycle -- that is the
  claim that a deeper check answers the same question about the same instant and
  only later, so a consumer owes it one more cycle and nothing else.

The stimulus is random insert/check/release/clear traffic over a deliberately
small object space, so ranges collide, entries go wild when they find no free
slot, and merges happen; a stream over a wide object space would exercise the
comparators and never the reduction.

Both simulators run it because they disagree about SystemVerilog in ways that
have mattered here before -- indexing a part-select is accepted by one and
rejected by the other -- so a single-simulator pass is not evidence the two
netlists are the same.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "rtl/test/tb_a3_dependence_table_depth.sv"
TABLE = ROOT / "rtl/abi3/ot_a3_dependence_table.sv"
PKG = ROOT / "rtl/abi3/ot_a3_pkg.sv"
VERILATOR = Path.home() / ".local/opentallas-tools/verilator-5.050/bin"


def reference_source(work: Path) -> Path:
    """The table as committed, renamed so it can sit beside the parameterised one.

    Taken from git rather than kept as a copy in the tree: a checked-in copy is a
    second source that drifts, and the claim is specifically about the committed
    module.
    """
    body = subprocess.run(
        ["git", "show", f"HEAD:rtl/abi3/ot_a3_dependence_table.sv"],
        cwd=ROOT, capture_output=True, check=True,
    ).stdout.decode()
    if "module ot_a3_dependence_table" not in body:
        raise SystemExit("HEAD's dependence table does not declare the module")
    renamed = body.replace(
        "module ot_a3_dependence_table", "module ot_a3_dependence_table_ref"
    )
    path = work / "ot_a3_dependence_table_ref.sv"
    path.write_text(renamed, encoding="utf-8")
    return path


def run_icarus(work: Path, sources: list[Path]) -> str:
    out = work / "depth.vvp"
    subprocess.run(
        ["iverilog", "-g2012", "-o", str(out), *[str(s) for s in sources]],
        cwd=work, check=True, capture_output=True,
    )
    return subprocess.run(
        ["vvp", str(out)], cwd=work, check=True, capture_output=True
    ).stdout.decode()


def run_verilator(work: Path, sources: list[Path]) -> str:
    env = dict(os.environ)
    env["PATH"] = f"{VERILATOR}:{env.get('PATH','')}"
    subprocess.run(
        ["verilator", "--binary", "-Wno-fatal", "--timing", "-o", "vdepth",
         *[str(s) for s in sources], "--top-module", BENCH.stem],
        cwd=work, check=True, capture_output=True, env=env,
    )
    return subprocess.run(
        [str(work / "obj_dir" / "vdepth")], cwd=work, check=True,
        capture_output=True, env=env,
    ).stdout.decode()


def parse(output: str) -> dict[str, int | bool]:
    match = re.search(
        r"cycles=(\d+) stage1_checks=(\d+) stage2_checks=(\d+) errors=(\d+)", output
    )
    if match is None:
        raise SystemExit(f"bench printed no summary:\n{output[-800:]}")
    return {
        "cycles": int(match.group(1)),
        "depth1_checks": int(match.group(2)),
        "depth2_checks": int(match.group(3)),
        "errors": int(match.group(4)),
        "pass": "PASS" in output,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / "results/rtl/a3_dependence_table_depth_campaign.json",
    )
    args = parser.parse_args()

    work = Path(tempfile.mkdtemp(prefix="a3-deptbl-depth-"))
    try:
        ref = reference_source(work)
        for source in (PKG, TABLE, BENCH):
            shutil.copy(source, work / source.name)
        sources = [work / PKG.name, ref, work / TABLE.name, work / BENCH.name]
        results = {
            "icarus": parse(run_icarus(work, sources)),
            "verilator": parse(run_verilator(work, sources)),
        }
    finally:
        shutil.rmtree(work, ignore_errors=True)

    agree = results["icarus"] == results["verilator"]
    report = {
        "schema": "opentallas.a3_dependence_table_depth.v1",
        "status": "pass" if all(r["pass"] for r in results.values()) and agree else "fail",
        "simulators_agree": agree,
        "results": results,
        "establishes": [
            "CHECK_STAGES = 1 is cycle-for-cycle identical to the module as "
            "committed, on both conflict outputs and on dbg_ranges_used",
            "CHECK_STAGES = 2 equals that reference delayed by exactly one cycle, "
            "so the deeper check answers the same question about the same instant",
        ],
        "does_not_establish": [
            "any frequency, area or throughput claim: this is behaviour only",
            "that a consumer tolerates the extra cycle -- ot_a3_microsequencer "
            "reads the conflict one cycle after the check and must be changed "
            "before CHECK_STAGES = 2 can be adopted in the control plane",
            "that the 2.00x sustained sizing in the iso-area audit is a result; "
            "that needs a closed routed record of the full control plane",
        ],
        "source_sha256": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (PKG, TABLE, BENCH, Path(__file__))
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(
        f"{report['status']}: {results['icarus']['cycles']} cycles, "
        f"{results['icarus']['depth1_checks']} depth-1 and "
        f"{results['icarus']['depth2_checks']} depth-2 comparisons, "
        f"{results['icarus']['errors']} errors; simulators agree: {agree}"
    )
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
