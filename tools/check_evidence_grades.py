#!/usr/bin/env python3
"""Refuse a claim whose evidence grade outruns its evidence.

Three numbers were wrong in this program in one night, and they failed the same
way rather than three ways:

  583 bytes per KV entry     graded "derived from official inference
                             implementation" -- it was a reading of that
                             implementation, which is a hypothesis, and running
                             it gave 1,024
  one hop per on-wafer       not graded at all: an assumption living inside a
  all-reduce                 model, where nothing could sweep it. A 681-region
                             all-reduce is 5.72 microseconds, not 0.20
  index scan threshold       graded "measured_bracket" -- a grade that does not
                             exist -- and it was an instrumentation artifact

So the discipline this file enforces is not "cite a source". Every graded entry
in technology.json already cites one. It is narrower and it is the thing that
actually failed:

  1. A grade must be one of the grades that are DEFINED. "measured_bracket" was
     not, and nothing rejected it. An undefined grade is a claim nobody agreed
     the meaning of.
  2. A grade that asserts execution must name an artifact that EXISTS, and that
     artifact must be in the repository rather than in a scratch directory. A
     citation to a file that is not there is not evidence, however true it was
     when written.
  3. "measured" means fabricated silicon in a peer-reviewed venue, and almost
     nothing we do is that. The honest grade for a number we obtained by running
     the reference implementation ourselves is `executed`, and it did not exist
     until these three defects showed that its absence was pushing values into
     grades that fitted them worse.

What this cannot check is whether an instrument was complete -- the index
threshold cited a real artifact that really did report zero. No file check
catches that. What catches it is noticing that a threshold falling exactly
between the tiled and the untiled rungs is a coincidence, and asking why.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterator

REPO = Path(__file__).resolve().parents[1]

#: `executed` claims WE ran something, so it must name a committed artifact.
#: `measured` claims SOMEONE ELSE measured fabricated silicon and published it,
#: so it must name a resolvable citation instead -- demanding a repository
#: artifact there would be asking us to hold a copy of a journal paper.
#: Conflating the two was this checker's own first defect.
SELF_EXECUTED_GRADES = {"executed"}
EXTERNALLY_MEASURED_GRADES = {"measured", "published"}
CITATION_PREFIXES = ("http://", "https://", "doi:", "10.")
#: A citation need not be a URL. "O'Connor et al., Fine-Grained DRAM, MICRO 2017"
#: is perfectly resolvable, and demanding a link would reject good scholarship
#: while admitting a bare link to anything. What a citation must have is a date:
#: something a reader can go and find. This checker's second defect was
#: rejecting seven sound citations to catch one bad one.
YEAR = re.compile(r"\b(19|20)\d{2}\b")


def _walk(node: Any, path: str = "") -> Iterator[tuple[str, dict[str, Any]]]:
    if isinstance(node, dict):
        if "grade" in node:
            yield path, node
        for key, value in node.items():
            yield from _walk(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _walk(value, f"{path}[{index}]")


def check(paths: list[Path], definitions: dict[str, str]) -> list[str]:
    problems: list[str] = []
    for path in paths:
        body = json.loads(path.read_text())
        for where, entry in _walk(body):
            grade = entry["grade"]
            if grade not in definitions:
                problems.append(
                    f"{path.name}{where}: grade {grade!r} is not defined. Defined "
                    f"grades are {sorted(definitions)}. An undefined grade is a claim "
                    "whose meaning nobody agreed."
                )
                continue
            if "source" not in entry and "evidence" not in entry:
                problems.append(f"{path.name}{where}: graded {grade!r} with no source")
            if grade in EXTERNALLY_MEASURED_GRADES:
                source = str(entry.get("source", ""))
                resolvable = source.startswith(CITATION_PREFIXES) or YEAR.search(source)
                if not resolvable:
                    problems.append(
                        f"{path.name}{where}: graded {grade!r}, which asserts someone "
                        f"published this, but its source names no document a reader "
                        f"could go and find -- no link, no DOI, no year: {source[:70]!r}"
                    )
            if grade in SELF_EXECUTED_GRADES:
                artifact = entry.get("artifact")
                if not artifact:
                    problems.append(
                        f"{path.name}{where}: graded {grade!r}, which asserts something "
                        "was run, but names no artifact holding the numbers"
                    )
                elif not (REPO / artifact).is_file():
                    problems.append(
                        f"{path.name}{where}: graded {grade!r} citing {artifact}, "
                        "which is not in the repository. A citation to a file that is "
                        "not there is not evidence."
                    )
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--technology", type=Path,
                        default=REPO / "configs/hardware/technology.json")
    parser.add_argument("--also", type=Path, action="append", default=[],
                        help="further graded files to check; repeat")
    args = parser.parse_args()

    definitions = json.loads(args.technology.read_text())["grade_definitions"]
    problems = check([args.technology, *args.also], definitions)

    print(f"grade vocabulary: {sorted(definitions)}")
    for path in [args.technology, *args.also]:
        graded = sum(1 for _ in _walk(json.loads(path.read_text())))
        shown = path.resolve()
        shown = shown.relative_to(REPO) if shown.is_relative_to(REPO) else shown
        print(f"  {shown}: {graded} graded entries")
    if problems:
        print(f"\n{len(problems)} problem(s):")
        for problem in problems:
            print(f"  {problem}")
        return 2
    print("\nevery graded entry names a defined grade and a source it can support")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
