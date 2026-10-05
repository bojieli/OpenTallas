#!/usr/bin/env python3
"""Refuse two state constants that share one code inside a module.

``ot_a3_vector_mhc_post.sv`` gained six pipelined-wait states numbered from 14,
and ``S_DONE`` was already 14. Nothing complains: both elaborators accept two
localparams with the same value, and a ``case`` with two arms for that value
simply takes the FIRST. So ``state <= S_DONE`` entered ``S_BRANCH_PIPE`` and
waited for a multiplier result nobody had issued. All six MHC_POST cases in
rtl/test/tb_a3_engine.sv deadlocked at their final commit, ``busy`` never
dropped, and every later case selecting that engine hung behind it -- 40
failures, 6 of them "engine never completed".

A cross-check by NAME cannot see this: every state was declared and every state
had an arm. Only the VALUES collide. So this walks each module's state-like
localparams and reports any code carrying more than one name, which is the shape
of that bug and is never intentional -- a deliberate alias would be written as
``localparam S_X = S_Y``, not as two independent literals.

Exit status is 1 if any collision is found, so this can gate.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "opentallas.derived.rtl_state_code_collisions.v1"
TOOL = "tools/audit_rtl_state_code_collisions.py"

#: ``localparam [4:0] S_IDLE = 5'd0;`` and the unsized and hex spellings.  A
#: state constant is recognised by its NAME, because a width-sized localparam is
#: how every other constant in this RTL is written too.
_DECL = re.compile(
    r"localparam\s*(?:\[[^\]]*\]\s*)?(S_[A-Za-z0-9_]+)\s*=\s*"
    r"(?:\d+\s*'\s*[dD]\s*(\d+)|\d+\s*'\s*[hH]\s*([0-9a-fA-F]+)|(\d+))\s*;"
)


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


def _modules(text: str) -> list[tuple[str, str]]:
    """``(module name, body)`` for each module in one file."""
    found: list[tuple[str, str]] = []
    starts = [
        (m.start(), m.group(1))
        for m in re.finditer(r"(?m)^\s*module\s+([A-Za-z_][A-Za-z0-9_$]*)", text)
    ]
    ends = [m.end() for m in re.finditer(r"(?m)^\s*endmodule", text)]
    for position, name in starts:
        stop = next((e for e in ends if e > position), len(text))
        found.append((name, text[position:stop]))
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results/rtl/state_code_collisions.json",
    )
    args = parser.parse_args()

    collisions: list[dict] = []
    scanned = 0
    for path in sorted((ROOT / "rtl").rglob("*.sv")):
        if "build" in path.relative_to(ROOT / "rtl").parts:
            continue
        try:
            text = _without_comments(path.read_text(encoding="utf-8"))
        except OSError:
            continue
        for module, body in _modules(text):
            by_code: dict[int, list[str]] = defaultdict(list)
            for match in _DECL.finditer(body):
                name = match.group(1)
                if match.group(2) is not None:
                    code = int(match.group(2))
                elif match.group(3) is not None:
                    code = int(match.group(3), 16)
                else:
                    code = int(match.group(4))
                by_code[code].append(name)
            if not by_code:
                continue
            scanned += 1
            for code, names in sorted(by_code.items()):
                if len(names) > 1:
                    collisions.append(
                        {
                            "file": str(path.relative_to(ROOT)),
                            "module": module,
                            "code": code,
                            "names": sorted(names),
                            "consequence": (
                                "a case with arms for several of these takes the "
                                "FIRST, so a transition to any of the others "
                                "silently enters that arm"
                            ),
                        }
                    )

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
        "modules_with_state_constants": scanned,
        "collision_count": len(collisions),
        "collisions": collisions,
        "not_a_claim": [
            "this reads localparams whose name starts with S_; a state encoded "
            "some other way is not covered",
            "a module with no collision is not thereby proved correct -- this "
            "finds one specific fault",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"{scanned} modules with state constants, {len(collisions)} collisions")
    for row in collisions:
        print(f"  {row['file']}:{row['module']} code {row['code']} -> "
              f"{', '.join(row['names'])}")
    print(f"-> {args.output}")
    return 1 if collisions else 0


if __name__ == "__main__":
    sys.exit(main())
