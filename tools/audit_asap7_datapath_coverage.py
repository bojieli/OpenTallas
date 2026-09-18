#!/usr/bin/env python3
"""Is every ABI 3.0 datapath module inside a block that has CLOSED on ASAP7?

``tools/audit_asap7_fmax_inventory.py`` names the slowest ABI 3.0 block with a
closed routed record and calls it the design's clock limiter.  That claim is only
as strong as its coverage, and the inventory says so itself: "a block with no
closed record at all is not on this list and could be slower".

Counting modules with their own record answers the wrong question.  Only 15 of
the 97 modules under ``rtl/abi3/`` have ever been routed *standalone*, but a
module does not need its own route -- ``ot_a3_event_scoreboard`` is inside
``ot_a3_g2_cluster``, which is routed and closed, so the scoreboard's paths were
timed as part of it.  What matters is whether each module is inside SOME closed
block, so this walks the instantiation graph from every closed top and reports
what the closure reaches and what it does not.

An uncovered module is not automatically a hole.  Three kinds are distinguished:

* **uncovered and instantiated** -- a real gap: something builds it and nothing
  that has closed contains it, so its frequency is unmeasured and the limiter
  claim does not cover it.
* **uncovered, instantiated by nothing** -- a top-level or a retired module.  A
  top is legitimately uncovered until it is routed; a retired one is covered by
  its replacement.
* **a blackbox or a package** -- carries no timing paths of its own.

Instantiation is read from the source with comments blanked first, because a
mention is not a binding: a module's header comment naming the module it replaces
would otherwise read as an instantiation.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "opentallas.derived.asap7_datapath_coverage.v1"
TOOL = "tools/audit_asap7_datapath_coverage.py"

INVENTORY = ROOT / "results/physical_abi3/asap7/frequency_inventory/asap7_fmax_inventory.json"

#: Modules that carry no timing paths of their own, so closure over them says
#: nothing.  A blackbox stands in for a compiled macro whose timing comes from
#: its liberty model, and a package declares types and constants.
NO_PATHS_SUFFIXES = ("_pkg", "_blackbox")


def _git_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _without_comments(text: str) -> str:
    """``text`` with SystemVerilog comments blanked, newlines preserved."""
    out = list(text)
    index = 0
    end = len(text)
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


_MODULE = re.compile(r"(?m)^\s*module\s+([A-Za-z_][A-Za-z0-9_$]*)")
#: An instantiation is ``name #(...) label (`` or ``name label (`` -- a module
#: name followed by an instance label and an open paren, at statement position.
#: Keywords that can precede a paren the same way are excluded by name.
_INSTANCE = re.compile(
    r"(?m)^\s*([A-Za-z_][A-Za-z0-9_$]*)\s*(?:#\s*\([^;]*?\)\s*)?"
    r"([A-Za-z_][A-Za-z0-9_$]*)\s*\("
)
_NOT_A_MODULE = frozenset(
    {
        "module", "endmodule", "if", "else", "for", "while", "case", "casez",
        "casex", "always", "always_ff", "always_comb", "always_latch", "assign",
        "initial", "final", "function", "task", "generate", "endgenerate",
        "begin", "end", "return", "assert", "assume", "cover", "wire", "reg",
        "logic", "input", "output", "inout", "parameter", "localparam",
        "typedef", "import", "export", "package", "endpackage", "interface",
        "genvar", "integer", "real", "time", "string", "bit", "byte", "int",
        "shortint", "longint", "unique", "priority", "do", "repeat", "forever",
        "fork", "join", "disable", "wait", "posedge", "negedge", "signed",
        "unsigned", "static", "automatic", "const", "ref", "void", "struct",
        "union", "enum", "default", "endcase", "endfunction", "endtask",
    }
)


def _sources() -> list[Path]:
    """Synthesisable sources: under rtl/, outside rtl/test/ and rtl/build/.

    ``rtl/build/`` holds campaign work directories with ANNOTATED COPIES of
    library modules -- ``ot_credit_manager`` appears in four files there and
    once for real.  Scanning them would concatenate a module's body with its
    copies and double-count every instantiation inside it.  No ``ot_a3_``
    module is duplicated that way today, so the ABI 3.0 figures are unchanged
    by this exclusion; it is the general correctness of the parse.
    """
    return [
        path
        for path in sorted((ROOT / "rtl").rglob("*.sv"))
        if not {"test", "build"} & set(path.relative_to(ROOT / "rtl").parts)
    ]


def _instantiation_graph() -> tuple[dict[str, set[str]], dict[str, str]]:
    """``module -> modules it instantiates``, and ``module -> defining file``."""
    defined: dict[str, str] = {}
    bodies: dict[str, str] = {}
    for path in _sources():
        try:
            text = _without_comments(path.read_text(encoding="utf-8"))
        except OSError:
            continue
        relative = str(path.relative_to(ROOT))
        starts = [(m.start(), m.group(1)) for m in _MODULE.finditer(text)]
        for index, (offset, name) in enumerate(starts):
            stop = starts[index + 1][0] if index + 1 < len(starts) else len(text)
            defined.setdefault(name, relative)
            bodies[name] = bodies.get(name, "") + text[offset:stop]
    graph: dict[str, set[str]] = {}
    for name, body in bodies.items():
        children: set[str] = set()
        for match in _INSTANCE.finditer(body):
            candidate = match.group(1)
            if candidate in _NOT_A_MODULE or candidate == name:
                continue
            if candidate in bodies:
                children.add(candidate)
        graph[name] = children
    return graph, defined


def _reachable(graph: dict[str, set[str]], roots: list[str]) -> set[str]:
    seen: set[str] = set()
    stack = [r for r in roots if r in graph]
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        stack.extend(graph.get(node, ()))
    return seen


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results/physical_abi3/asap7/datapath_coverage.json",
    )
    args = parser.parse_args()

    if not INVENTORY.exists():
        print(f"{INVENTORY} is absent; run the fmax inventory first", file=sys.stderr)
        return 1
    inventory = json.loads(INVENTORY.read_text())
    closed_blocks = [
        entry["block"]
        for entry in inventory["best_closed_fmax_per_block_slowest_first"]
    ]
    limiter = inventory.get("clock_limiter") or {}

    graph, defined = _instantiation_graph()
    covered = _reachable(graph, closed_blocks)

    instantiated_by: dict[str, set[str]] = {name: set() for name in graph}
    for parent, children in graph.items():
        for child in children:
            instantiated_by.setdefault(child, set()).add(parent)

    datapath = sorted(name for name in graph if name.startswith("ot_a3_"))
    rows: list[dict[str, Any]] = []
    for name in datapath:
        no_paths = name.endswith(NO_PATHS_SUFFIXES)
        parents = sorted(instantiated_by.get(name, ()))
        rows.append(
            {
                "module": name,
                "file": defined.get(name),
                "covered_by_a_closed_block": name in covered,
                "has_its_own_closed_record": name in closed_blocks,
                "carries_no_timing_paths": no_paths,
                "instantiated_by": parents,
            }
        )

    # Top-level islands: a module nothing instantiates is the root of a
    # separately-elaborated subsystem.  Their number and what each reaches is the
    # shape of the design as the RTL actually assembles it, and it decides what a
    # per-block frequency is a statement ABOUT.
    # Scoped to this audit's subject.  The graph also holds probe wrappers,
    # ``ot_fp32_*`` primitives and any ``tb_*`` top that sits outside rtl/test/,
    # and each of those is a root nothing instantiates without being a subsystem
    # of the design.
    islands = sorted(
        name
        for name in graph
        if not instantiated_by.get(name) and name.startswith("ot_a3_")
    )
    island_rows = []
    for name in islands:
        members = sorted(_reachable(graph, [name]))
        island_rows.append(
            {
                "top": name,
                "modules_reached": len(members),
                "members": members,
                "has_a_closed_record": name in closed_blocks,
            }
        )
    island_rows.sort(key=lambda row: -row["modules_reached"])

    gaps = [
        r
        for r in rows
        if not r["covered_by_a_closed_block"]
        and not r["carries_no_timing_paths"]
        and r["instantiated_by"]
    ]
    tops = [
        r
        for r in rows
        if not r["covered_by_a_closed_block"]
        and not r["carries_no_timing_paths"]
        and not r["instantiated_by"]
    ]
    no_paths = [r for r in rows if r["carries_no_timing_paths"]]

    report = {
        "schema": SCHEMA,
        "producer": {"tool": TOOL, "git": {"commit": _git_commit()}},
        "question": (
            "The fmax inventory calls the slowest ABI 3.0 block with a closed "
            "routed record the design's clock limiter.  Is every ABI 3.0 datapath "
            "module inside SOME block that has closed, so that the limiter covers "
            "the datapath rather than only the blocks that happen to have been "
            "routed?"
        ),
        "method": (
            "Reads the instantiation graph out of every synthesisable source under "
            "rtl/ (rtl/test/ excluded) with comments BLANKED first -- a mention is "
            "not a binding -- then takes the transitive closure from each block "
            "that has a closed routed record.  A module inside that closure had "
            "its paths timed as part of a block that closed, whether or not it was "
            "ever routed standalone."
        ),
        "counts": {
            "abi3_modules": len(rows),
            "with_their_own_closed_record": sum(
                1 for r in rows if r["has_its_own_closed_record"]
            ),
            "covered_by_a_closed_block": sum(
                1 for r in rows if r["covered_by_a_closed_block"]
            ),
            "carry_no_timing_paths": len(no_paths),
            "uncovered_and_instantiated": len(gaps),
            "uncovered_and_instantiated_by_nothing": len(tops),
        },
        "limiter_under_audit": limiter,
        "top_level_islands": {
            "what": (
                "A module nothing instantiates is the root of a separately "
                "elaborated subsystem.  No single top integrates this design, so "
                "every ASAP7 frequency is a statement about ONE island, and a "
                "whole-chip clock has not been measured because no netlist "
                "contains the whole chip."
            ),
            "count": len(island_rows),
            "with_a_closed_record": sum(
                1 for row in island_rows if row["has_a_closed_record"]
            ),
            "islands": island_rows,
        },
        "uncovered_and_instantiated": [
            {"module": r["module"], "instantiated_by": r["instantiated_by"]}
            for r in gaps
        ],
        "uncovered_and_instantiated_by_nothing": [r["module"] for r in tops],
        "carry_no_timing_paths": [r["module"] for r in no_paths],
        "modules": rows,
        "not_a_claim": [
            "coverage is not a frequency: a module inside a closed block met that "
            "block's target, which may be looser than the module's own ceiling",
            "ASAP7 is a predictive, non-manufacturable academic PDK",
            "a module instantiated by nothing is a top-level or a retired module; "
            "which of the two it is cannot be read off the graph and is not "
            "guessed at here",
            "the instantiation regex reads ``name [#(...)] label (`` at statement "
            "position and drops SystemVerilog keywords by name; it is a parse of "
            "convention, not a full elaboration",
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report["counts"], indent=1, sort_keys=True))
    print(f"\ntop-level islands: {len(island_rows)} "
          f"({report['top_level_islands']['with_a_closed_record']} with a closed record)")
    for row in island_rows[:8]:
        mark = "closed" if row["has_a_closed_record"] else "  --  "
        print(f"  {mark}  {row['modules_reached']:3d} modules  {row['top']}")
    if gaps:
        print("\nUNCOVERED and instantiated -- the limiter does not cover these:")
        for row in gaps:
            print(f"  {row['module']:38s} built by {', '.join(row['instantiated_by'])}")
    if tops:
        print("\nuncovered, instantiated by nothing (top-level or retired):")
        for row in tops:
            print(f"  {row['module']}")
    print(f"\n-> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
