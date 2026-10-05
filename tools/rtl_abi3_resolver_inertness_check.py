#!/usr/bin/env python3
"""Is the disabled build of the resolver optimisation the block that shipped?

Two optimisations live behind two parameters in the view-resolution path:

  * ``FAST_SCAN`` (ot_a3_resolver_bank) elides the per-slot scan state.
  * ``FAST_WALK`` (ot_a3_view_resolver, forwarded by the bank) folds S_SELECT
    into the states that already advance the term, and pairs the bounding
    walk's accumulate with the next axis's operand presentation.

Both default to 0, and both are plumbed up through ot_a3_microsequencer,
ot_a3_device_top and rtl/test/a3_microsequencer_top.sv so a campaign can set
them from the top.  This tool answers the question that a fast-versus-slow
equivalence bench structurally cannot: is the DISABLED build the block as it
shipped, or is it a third design that nobody measured?

It is worth having as a tool rather than a bench alone because the reference
side must not be a hand-kept copy.  ``SHIPPED_COMMIT`` names the commit whose
rtl/abi3/ot_a3_view_resolver.sv and rtl/abi3/ot_a3_resolver_bank.sv are the
shipped blocks; this tool reads them out of git, renames only the module
identifiers, and elaborates them beside the working tree's build.  A copy
checked into rtl/test/ would rot silently; a copy taken from git cannot.

The bar is cycle-exact identity, not equal results: every output, the
descriptor port's request and ID, and the shared divider's request vector are
compared on every clock edge out of reset, an aborted transaction included.  A
disabled optimisation that runs even one cycle faster is the defect this
checks for.

  python3 tools/rtl_abi3_resolver_inertness_check.py [--output PATH]

What this does NOT establish: the whole-design count.  That is
tools/rtl_abi3_deployment_campaign.py, whose committed per-case
rtl_transaction_cycles the disabled build must reproduce exactly.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

# The commit whose resolver sources are "the block as it shipped".  This is a
# deliberate pin, not a moving reference: after the optimisation lands, HEAD's
# copy of these files is the optimised one, so a tool that read HEAD would be
# comparing the change with itself.  Re-pin this only together with a fresh
# argument for why the new commit's blocks are the reference, and re-run the
# deployment campaign in the same change.
SHIPPED_COMMIT = "4b1fc50"

SHIPPED_SOURCES = {
    "rtl/abi3/ot_a3_view_resolver.sv": "ot_a3_view_resolver",
    "rtl/abi3/ot_a3_resolver_bank.sv": "ot_a3_resolver_bank",
}
SUFFIX = "_shipped"

# The working tree's build, the bench, and what they need.
WORKING_SOURCES = (
    "rtl/abi3/ot_a3_pkg.sv",
    "rtl/abi3/ot_a3_shared_divider.sv",
    "rtl/abi3/ot_a3_view_resolver.sv",
    "rtl/abi3/ot_a3_resolver_bank.sv",
)
BENCHES = {
    # top module -> (bench source, the claim it settles)
    "tb_a3_resolver_bank_inert": (
        "rtl/test/tb_a3_resolver_bank_inert.sv",
        "FAST_SCAN=0 FAST_WALK=0 is cycle-exactly the shipped block",
    ),
    "tb_a3_resolver_bank_equiv": (
        "rtl/test/tb_a3_resolver_bank_equiv.sv",
        "the enabled walk publishes what the disabled walk publishes",
    ),
}

PASS_RE = re.compile(r"^PASS:", re.M)
FAIL_RE = re.compile(r"^FAIL", re.M)
COUNTS_RE = re.compile(r"cases=(\d+) checks=(\d+) mismatches=(\d+)")
EDGES_RE = re.compile(r"edges compared=(\d+) differences=(\d+)")


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(ROOT), *args],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise SystemExit(
            f"git {' '.join(args)} failed: {result.stderr.strip()}"
        )
    return result.stdout


def shipped_copy(path: str, module: str) -> str:
    """That file at SHIPPED_COMMIT, with only its module identifiers renamed.

    Nothing else is touched: no parameter is added, no line is reflowed.  The
    rename is anchored on a word boundary so a mention inside a comment is
    renamed too, which keeps the two copies textually diffable.
    """
    body = git("show", f"{SHIPPED_COMMIT}:{path}")
    if "FAST_SCAN" in body or "FAST_WALK" in body:
        raise SystemExit(
            f"{path} at {SHIPPED_COMMIT} already carries the optimisation's "
            "parameters; SHIPPED_COMMIT is pinned to the wrong commit and the "
            "comparison would be the change against itself"
        )
    for name in SHIPPED_SOURCES.values():
        body = re.sub(rf"\b{name}\b", name + SUFFIX, body)
    if f"module {module}{SUFFIX}" not in body:
        raise SystemExit(f"{path}: could not rename module {module}")
    return body


def run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=None,
        help="write the result as JSON here (default: report on stdout only)",
    )
    parser.add_argument(
        "--keep", action="store_true",
        help="keep the build directory and print its path",
    )
    args = parser.parse_args()

    build = Path(tempfile.mkdtemp(prefix="opentallas-resolver-inert-"))
    try:
        shipped_files = []
        for path, module in SHIPPED_SOURCES.items():
            name = Path(path).stem + SUFFIX + ".sv"
            (build / name).write_text(shipped_copy(path, module),
                                      encoding="utf-8")
            shipped_files.append(str(build / name))

        results: list[dict[str, Any]] = []
        ok = True
        for top, (bench, claim) in BENCHES.items():
            sources = [str(ROOT / s) for s in WORKING_SOURCES]
            # only the inertness bench needs the shipped copies
            if top == "tb_a3_resolver_bank_inert":
                sources += shipped_files
            sources.append(str(ROOT / bench))
            binary = f"{top}.vvp"
            rc, log = run(
                ["iverilog", "-g2012", "-s", top, "-o", binary, *sources],
                build,
            )
            record: dict[str, Any] = {
                "bench": bench, "top": top, "claim": claim,
                "compiled": rc == 0,
            }
            if rc == 0:
                rc, log = run(["vvp", binary], build)
                record["returncode"] = rc
                counts = COUNTS_RE.search(log)
                if counts:
                    record["cases"] = int(counts.group(1))
                    record["checks"] = int(counts.group(2))
                    record["mismatches"] = int(counts.group(3))
                edges = EDGES_RE.search(log)
                if edges:
                    record["edges_compared"] = int(edges.group(1))
                    record["edge_differences"] = int(edges.group(2))
                record["passed"] = bool(
                    rc == 0 and PASS_RE.search(log) and not FAIL_RE.search(log)
                )
            else:
                record["passed"] = False
            record["log_tail"] = "\n".join(log.strip().splitlines()[-8:])
            ok = ok and record["passed"]
            results.append(record)
            print(f"--- {top}: {'PASS' if record['passed'] else 'FAIL'}")
            print(record["log_tail"])

        report = {
            "schema": "opentallas.rtl.resolver_inertness.v1",
            "shipped_commit": SHIPPED_COMMIT,
            "shipped_commit_resolved": git(
                "rev-parse", SHIPPED_COMMIT).strip(),
            "shipped_sources": sorted(SHIPPED_SOURCES),
            "definition": (
                "the disabled build (FAST_SCAN=0, FAST_WALK=0) is compared "
                "cycle by cycle with a verbatim copy of the shipped blocks "
                "taken from git, on one stimulus: every output, the "
                "descriptor port's request and ID, and the shared divider's "
                "request vector, on every clock edge out of reset"
            ),
            "not_established_here": (
                "the whole-design cycle count; the disabled build must also "
                "reproduce the committed per-case rtl_transaction_cycles of "
                "results/rtl/abi3_deployment_campaign.json exactly"
            ),
            "benches": results,
            "status": "pass" if ok else "fail",
        }
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(report, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            print(f"wrote {args.output}")
        print("status:", report["status"])
        return 0 if ok else 1
    finally:
        if args.keep:
            print("build directory:", build)
        else:
            shutil.rmtree(build, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
