#!/usr/bin/env python3
"""Combinational loops that CARRY a value across their iterations.

``ot_a3_attention_softmax_block`` took its maximum over LANES valid lanes with one
``always @*`` loop that assigned ``max_scan`` from ``max_scan``. That is a FOLD,
and a fold is a CHAIN: at LANES = 64 it synthesised as sixty-four 32-bit
compare-and-selects in series. Routed, the worst path was ``scores[47]`` to
``block_max[30]`` through 2,610 cells, 35.2 ns, and the block came back at
28.4 MHz. Rewritten as a balanced tree -- six levels, and bit-identical because
both keep the lowest-index maximal lane -- it routed at **257.3 MHz over FEWER
cells**, 9.06x. ``ot_a3_attention_denominator`` instantiates that block and was
28.5 MHz for the same reason, so one rewrite reached two rungs.

Nothing warns about this. The source is short and reads like a reduction; the depth
only appears in a routed path report, which costs hours per module. So this finds
the shape statically: a variable assigned inside a `for` in a combinational
`always` block, whose right-hand side reads the same variable.

Not every hit is a fault. A one-bit OR or AND fold is a chain of trivial gates that
the mapper flattens, and a loop over two or four elements is already shallow. The
report gives the carried variable's width and the loop's trip count so the caller
can judge, and orders by trip count times width -- the product that became 2,610
cells.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "opentallas.derived.rtl_combinational_folds.v1"
TOOL = "tools/audit_rtl_combinational_folds.py"


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


def _widths(text: str) -> dict[str, int]:
    """``reg``/``wire`` declared widths, as a best-effort count of bits."""
    found: dict[str, int] = {}
    for m in re.finditer(
        r"\b(?:reg|wire|logic)\b\s*(?:\[\s*([^\]:]+?)\s*:\s*([^\]]+?)\s*\])?\s*"
        r"([A-Za-z_]\w*)\s*(?:;|,|=)",
        text,
    ):
        high, low, name = m.group(1), m.group(2), m.group(3)
        if high is None:
            found.setdefault(name, 1)
            continue
        try:
            found.setdefault(name, abs(int(high) - int(low)) + 1)
        except ValueError:
            found.setdefault(name, 0)  # parameterised; unknown
    return found


def _trip(bound: str, params: dict[str, int]) -> int:
    bound = bound.strip()
    if bound.isdigit():
        return int(bound)
    return params.get(bound, 0)


def _params(text: str) -> dict[str, int]:
    found: dict[str, int] = {}
    for m in re.finditer(
        r"\b(?:parameter|localparam)\b[^;=]*?\b([A-Za-z_]\w*)\s*=\s*(\d+)", text
    ):
        found.setdefault(m.group(1), int(m.group(2)))
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results/rtl/combinational_folds.json",
    )
    parser.add_argument(
        "--min-product",
        type=int,
        default=64,
        help="report a fold only when trip count x carried width reaches this",
    )
    args = parser.parse_args()

    folds: list[dict] = []
    scanned = 0
    for path in sorted((ROOT / "rtl").rglob("*.sv")):
        parts = set(path.relative_to(ROOT / "rtl").parts)
        if "build" in parts:
            continue
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            continue
        text = _without_comments(raw)
        scanned += 1
        widths = _widths(text)
        params = _params(text)
        #: combinational always blocks AND FUNCTIONS.  A function body is
        #: combinational by definition, and the deepest fold in this project was
        #: in one: ``fp32_add_rne``'s 27-iteration cancellation normalize in
        #: rtl/ot_fp32_rne_pkg.sv, which is 64% of a routed 10.6 ns path in
        #: ot_a3_qwen_gqa and reaches every module that calls the scalar
        #: authority. The first version of this audit scanned only ``always``
        #: blocks and reported that file as clean.
        for block in re.finditer(
            r"\b(?:always\s*(?:@\s*\*|@\s*\(\s*\*\s*\)|_comb\b)"
            r"|function\b[^;]*?;)((?:.|\n)*?)"
            r"(?=\n\s*(?:always|assign|endmodule|endfunction|endtask|initial"
            r"|function|task)\b)",
            text,
        ):
            body = block.group(1)
            line = text[: block.start()].count("\n") + 1
            for loop in re.finditer(
                r"for\s*\(\s*\w+\s*=\s*[^;]+;\s*\w+\s*<\s*([^;)]+?)\s*;", body
            ):
                trip = _trip(loop.group(1), params)
                tail = body[loop.end():]
                #: assignments in the loop whose right-hand side reads the target
                #: a BLOCKING assignment, and nothing else.  Without excluding
                #: the comparison and non-blocking operators, ``if (state == S_X)``
                #: reads as an assignment to ``state`` whose right-hand side runs
                #: to the next semicolon -- which is how the first version of this
                #: audit put a 4-bit sequential state register at the top of its
                #: own report.
                for assign in re.finditer(
                    r"(\w+)\s*(?<![<>!=])=(?!=)\s*([^;]+);", tail[:2000]
                ):
                    name, rhs = assign.group(1), assign.group(2)
                    if not re.search(rf"\b{re.escape(name)}\b", rhs):
                        continue
                    width = widths.get(name, 0)
                    product = trip * width
                    if product < args.min_product:
                        continue
                    folds.append(
                        {
                            "file": str(path.relative_to(ROOT)),
                            "always_block_line": line,
                            "carried": name,
                            "carried_width_bits": width,
                            "loop_bound": loop.group(1).strip(),
                            "trip_count": trip,
                            "product": product,
                        }
                    )
    #: one row per (file, carried) -- a fold reassigned in several branches of the
    #: same loop is ONE chain, not several
    unique: dict[tuple, dict] = {}
    for row in folds:
        key = (row["file"], row["carried"], row["always_block_line"])
        if key not in unique or row["product"] > unique[key]["product"]:
            unique[key] = row
    rows = sorted(unique.values(), key=lambda r: -r["product"])

    report = {
        "schema": SCHEMA,
        "producer": {
            "tool": TOOL,
            "git": {
                "commit": subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=True,
                ).stdout.strip()
            },
        },
        "files_scanned": scanned,
        "min_product": args.min_product,
        "fold_count": len(rows),
        "folds": rows,
        "not_a_claim": [
            "a fold is not automatically a fault: a one-bit OR or AND chain maps to "
            "trivial gates and a trip count of two or four is already shallow",
            "this is a regex over comment-stripped source, not an elaboration; a "
            "carried value the pattern does not recognise is missed, and a width "
            "given as a parameter expression is reported as 0 and sorts last",
            "the product is a proxy for depth, not a delay",
            "function bodies are scanned as well as always blocks, because the "
            "deepest fold in this tree is inside a package function",
            "blocking assignments only: comparisons and non-blocking assignments "
            "are excluded, because reading `if (state == S_X)` as an assignment is "
            "exactly how the first version of this audit misreported a sequential "
            "state register as the deepest fold in the tree",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"{scanned} files scanned, {len(rows)} carried folds at product >= {args.min_product}")
    for row in rows[:20]:
        print(f"  {row['product']:6}  {row['carried']:22} {row['carried_width_bits']:3}b "
              f"x {row['trip_count']:4}  {row['file']}:{row['always_block_line']}")
    print(f"-> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
