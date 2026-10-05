#!/usr/bin/env python3
"""Emit a route plan for the ABI 3.0 modules no closed block covers.

``tools/audit_asap7_datapath_coverage.py`` reports which modules are inside a
block that has closed on ASAP7 and which are not.  Closing that gap means
routing the uncovered ones, and each route needs the module's file plus every
file that defines something it instantiates, plus the packages it imports --
assembled by hand that is where a route dies ten minutes in on a missing source.

So this derives the source list from the same instantiation graph the coverage
audit walks, orders the modules so the cheapest and most-shared come first, and
writes one shell command per module.  Nothing is launched: the plan is the
output, because a route is minutes of a shared machine and the ceiling of four
concurrent ORFS runs is a decision for the caller.

Ordering is by fan-in then by size.  A module many parents instantiate bounds all
of them at once, which is the most a single route can buy; among equals the
smaller file is the shorter synthesis.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "opentallas.derived.asap7_coverage_route_plan.v1"
TOOL = "tools/plan_asap7_coverage_routes.py"
COVERAGE = ROOT / "results/physical_abi3/asap7/datapath_coverage.json"

#: Packages are not modules, so the graph does not carry them; an import is how
#: a module names one and the file order must put them first.
_IMPORT = re.compile(r"(?m)^\s*import\s+([A-Za-z_][A-Za-z0-9_$]*)\s*::")
_PKG_REF = re.compile(r"([A-Za-z_][A-Za-z0-9_$]*)\s*::")


def _git_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _without_comments(text: str) -> str:
    out = list(text)
    index, end = 0, len(text)
    while index < end:
        if text.startswith("//", index):
            stop = text.find("\n", index)
            stop = end if stop < 0 else stop
            for position in range(index, stop):
                out[position] = " "
            index = stop
        elif text.startswith("/*", index):
            stop = text.find("*/", index + 2)
            stop = end if stop < 0 else stop + 2
            for position in range(index, stop):
                if out[position] != "\n":
                    out[position] = " "
            index = stop
        else:
            index += 1
    return "".join(out)


def _package_files() -> dict[str, str]:
    """``package name -> defining file``, over the synthesisable sources."""
    found: dict[str, str] = {}
    for path in sorted((ROOT / "rtl").rglob("*.sv")):
        if {"test", "build"} & set(path.relative_to(ROOT / "rtl").parts):
            continue
        try:
            text = _without_comments(path.read_text(encoding="utf-8"))
        except OSError:
            continue
        for match in re.finditer(r"(?m)^\s*package\s+([A-Za-z_][A-Za-z0-9_$]*)", text):
            found.setdefault(match.group(1), str(path.relative_to(ROOT)))
    return found


def _packages_named(files: list[str]) -> list[str]:
    """Every package name referenced by ``files``, import or ``pkg::`` alike."""
    names: set[str] = set()
    for relative in files:
        try:
            text = _without_comments((ROOT / relative).read_text(encoding="utf-8"))
        except OSError:
            continue
        names.update(_IMPORT.findall(text))
        names.update(_PKG_REF.findall(text))
    return sorted(names)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results/physical_abi3/asap7/coverage_route_plan.json",
    )
    parser.add_argument("--clock-period-ns", type=float, default=2.0)
    parser.add_argument(
        "--limit", type=int, default=0, help="plan at most this many routes (0 = all)"
    )
    args = parser.parse_args()

    coverage = json.loads(COVERAGE.read_text())
    rows = {r["module"]: r for r in coverage["modules"]}
    # The FULL graph, not the abi3-filtered rows.  Deriving children from
    # ``instantiated_by`` on the rows alone loses every child whose name carries
    # no ``ot_a3_`` prefix: ``ot_a3_mac_lane_pipe`` instantiates
    # ``ot_mac_bf16_fp32_pipe``, the route omitted that file, and yosys refused
    # with "Module `\\ot_mac_bf16_fp32_pipe' ... is not part of the design".
    graph = coverage.get("instantiation_graph")
    file_of = coverage.get("file_of_module") or {}
    if graph:
        children = {name: set(kids) for name, kids in graph.items()}
    else:  # an older report without the full graph
        children = {r["module"]: set() for r in coverage["modules"]}
        for row in coverage["modules"]:
            for parent in row["instantiated_by"]:
                if parent in children:
                    children[parent].add(row["module"])

    packages = _package_files()
    targets = [r["module"] for r in coverage["uncovered_and_instantiated"]]

    def descendants(name: str) -> set[str]:
        seen: set[str] = set()
        stack = [name]
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            stack.extend(children.get(node, ()))
        return seen

    plans: list[dict[str, Any]] = []
    for name in targets:
        row = rows[name]
        family = sorted(descendants(name))
        files: list[str] = []
        for member in family:
            path = rows.get(member, {}).get("file") or file_of.get(member)
            if path and path not in files:
                files.append(path)
        needed = [
            packages[p] for p in _packages_named(files) if p in packages
        ]
        ordered = [f for f in dict.fromkeys(needed)] + [
            f for f in files if f not in needed
        ]
        size = sum(
            (ROOT / f).stat().st_size for f in ordered if (ROOT / f).exists()
        )
        plans.append(
            {
                "module": name,
                "fan_in": len(row["instantiated_by"]),
                "instantiated_by": row["instantiated_by"],
                "submodules": len(family) - 1,
                "sources": ordered,
                "source_bytes": size,
                "command": " ".join(
                    [
                        "PYTHONPATH=. python3 tools/run_abi3_physical.py",
                        "--view asap7",
                        f"--top {name}",
                        *(f"--source {f}" for f in ordered),
                        f"--clock-period-ns {args.clock_period_ns:g}",
                        "--stages pnr",
                        "--purpose characterization",
                        "--false-path-from rst_n",
                        "--slew-margin-percent 60",
                    ]
                ),
            }
        )

    # Most-shared first, then smallest: a module many parents build bounds all of
    # them with one route, and among equals the smaller source synthesises sooner.
    plans.sort(key=lambda p: (-p["fan_in"], p["source_bytes"]))
    if args.limit:
        plans = plans[: args.limit]

    report = {
        "schema": SCHEMA,
        "producer": {"tool": TOOL, "git": {"commit": _git_commit()}},
        "derived_from": str(COVERAGE.relative_to(ROOT)),
        "clock_period_ns": args.clock_period_ns,
        "ordering": (
            "fan-in descending, then source bytes ascending: a module many "
            "parents instantiate bounds all of them with one route, and among "
            "equals the smaller source synthesises sooner"
        ),
        "route_count": len(plans),
        "routes": plans,
        "not_a_claim": [
            "nothing is launched here; ORFS runs of ONE top collide on "
            "DESIGN_NICKNAME and four concurrent runs is the practical ceiling, "
            "so scheduling is the caller's",
            "the source list is derived from an instantiation parse, not an "
            "elaboration: a module reached only through a generate construct the "
            "regex does not read would be missing and the route would say so",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"{len(plans)} routes planned at {args.clock_period_ns:g} ns")
    for plan in plans[:14]:
        print(
            f"  fan-in {plan['fan_in']:2d}  subs {plan['submodules']:2d}  "
            f"{plan['source_bytes']:7d}B  {plan['module']}"
        )
    print(f"-> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
