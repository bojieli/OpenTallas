#!/usr/bin/env python3
"""Prove an RTL rewrite computes what the module it replaced computed.

An optimisation that changes a module's structure needs a gate stronger than "the
existing bench still passes": a bench written for the reference decode covers the
cases the reference cared about, not the cases the rewrite could newly get wrong.
The gate that fits is a MITER -- the old module and the new one, identical inputs,
every output compared -- and the old module is already in git.

So this extracts the pre-edit module from a revision, renames it to ``<top>_ref``
so both can be elaborated at once, compiles the miter bench against both, and runs
it at each requested parameter value.  The bench decides what to drive; this
decides nothing about the function and only reports whether every vector agreed.

``--slots`` values are passed to the bench's own top parameter, so a bench can
enumerate a small instance exhaustively and drive the shipped width structurally.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
SCHEMA = "opentallas.derived.rtl_rewrite_equivalence.v1"


def _run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top", required=True, help="the module that was rewritten")
    parser.add_argument(
        "--revision",
        default="HEAD~1",
        help="the revision holding the module as it stood BEFORE the rewrite",
    )
    parser.add_argument("--bench", required=True, type=Path, help="the miter bench")
    parser.add_argument(
        "--bench-top", default=None, help="the bench's module name (default: its stem)"
    )
    parser.add_argument(
        "--source",
        action="append",
        default=[],
        type=Path,
        help="repo-relative sources, packages first; the rewritten module included",
    )
    parser.add_argument(
        "--parameter",
        default="SLOTS",
        help="the bench parameter each --at value is bound to",
    )
    parser.add_argument(
        "--at",
        action="append",
        type=int,
        default=[],
        help="one bench run per value (e.g. --at 8 --at 64)",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    bench_top = args.bench_top or args.bench.stem
    reference_module = f"{args.top}_ref"

    blob = _run(["git", "show", f"{args.revision}:{_relative(args.source, args.top)}"], REPO)
    if blob.returncode != 0:
        print(f"cannot read {args.top} at {args.revision}: {blob.stderr}", file=sys.stderr)
        return 2
    renamed = re.sub(
        rf"\bmodule\s+{re.escape(args.top)}\b", f"module {reference_module}", blob.stdout
    )
    if reference_module not in renamed:
        print(f"{args.top} is not declared at {args.revision}", file=sys.stderr)
        return 2

    runs: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory() as scratch:
        work = Path(scratch)
        (work / "ref.sv").write_text(renamed)
        for value in args.at or [0]:
            compile_command = ["iverilog", "-g2005-sv"]
            if args.at:
                compile_command += [f"-P{bench_top}.{args.parameter}={value}"]
            compile_command += ["-o", str(work / f"m{value}.vvp")]
            compile_command += [str(REPO / source) for source in args.source]
            compile_command += [str(work / "ref.sv"), str(REPO / args.bench)]
            built = _run(compile_command, work)
            if built.returncode != 0:
                runs.append(
                    {
                        "at": value,
                        "compiled": False,
                        "passed": False,
                        "detail": built.stderr.strip()[-600:],
                    }
                )
                continue
            ran = _run([str(work / f"m{value}.vvp")], work)
            tail = (ran.stdout or "").strip().splitlines()
            verdict = next((line for line in reversed(tail) if "PASS" in line or "FAIL" in line), "")
            runs.append(
                {
                    "at": value,
                    "compiled": True,
                    "passed": verdict.startswith("PASS"),
                    "verdict": verdict.strip(),
                }
            )
            print(f"  {args.parameter}={value}: {verdict.strip() or '(no verdict line)'}")

    every = bool(runs) and all(run["passed"] for run in runs)
    report = {
        "schema": SCHEMA,
        "question": (
            f"does {args.top} as it now stands compute what it computed at "
            f"{args.revision}?"
        ),
        "answer": "yes, on every vector the miter drove" if every else "NO",
        "top": args.top,
        "reference_module": reference_module,
        "reference_revision": args.revision,
        "reference_revision_sha": _run(
            ["git", "rev-parse", args.revision], REPO
        ).stdout.strip(),
        "bench": str(args.bench),
        "sources": [str(source) for source in args.source],
        "runs": runs,
        "equivalent": every,
        "not_a_claim": [
            "this is equivalence over the vectors the BENCH drives, not a formal "
            "proof; the bench's own coverage is the strength of the claim",
            "it says nothing about timing, area or power -- a route says that",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(f"\nequivalent: {every}\n-> {args.output}")
    return 0 if every else 1


def _relative(sources: list[Path], top: str) -> str:
    """The source that declares ``top``, as git needs to address it."""
    for source in sources:
        text = (REPO / source).read_text(encoding="utf-8")
        if re.search(rf"\bmodule\s+{re.escape(top)}\b", text):
            return str(source)
    return f"rtl/abi3/{top}.sv"


if __name__ == "__main__":
    raise SystemExit(main())
