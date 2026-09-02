#!/usr/bin/env python3
"""Inventory every unit-bearing numeric claim candidate in release Markdown.

This is deliberately a census, not a claim that all prose is proven.  Every
number followed by one of the units used by the evidence-ledger audit is
recorded and classified as provenance-bound, unbound, or explicitly excluded
because it is inside a fenced block or HTML comment (or is a hexadecimal
``0x`` prefix).  The checked-in canonical snapshot makes additions and
classification changes visible even when a writer has not added a ``figure:``
annotation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Sequence

REPO = Path(__file__).resolve().parents[1]
TOOLS = Path(__file__).resolve().parent
DEFAULT_OUTPUT = Path("results/abi3/prose_figure_coverage.json")

# Invoking this file directly puts tools/, rather than the repository root, on
# sys.path.  The checker lives beside it and is the authority for annotation
# parsing, scope attachment, and written-precision comparisons.
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from check_prose_figures import (  # noqa: E402
    ANY_COMMENT,
    NUMBER,
    Annotation,
    _fenced_spans,
    agree,
    leading_number,
    scan,
)

SCHEMA = "opentallas.prose_figure_coverage.v1"
CLASSIFICATIONS = ("provenance_bound", "unbound", "excluded_context")
CLAIM_UNITS = ("tok/s", "TB/s", "mm²", "µs", ":1", "GB", "W", "×", "x", "%")
_UNIT_PATTERN = (
    r"tok/s(?![A-Za-z0-9])|TB/s(?![A-Za-z0-9])|mm²(?![A-Za-z0-9])|"
    r"µs(?![A-Za-z0-9])|:1(?![0-9])|GB(?![A-Za-z])|W(?![A-Za-z])|×|x|%"
)
CLAIM_CANDIDATE = re.compile(
    rf"(?<![A-Za-z0-9_.])(?P<number>{NUMBER.pattern})"
    rf"(?P<space>(?:[ \t]*-?[ \t]*|[ \t]*\r?\n[ \t]*))"
    rf"(?P<unit>{_UNIT_PATTERN})"
)


def canonical_json(value: Any) -> bytes:
    """Return the repository's deterministic compact JSON representation."""

    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return (payload + "\n").encode("ascii")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def corpus_documents(repo: Path = REPO) -> list[Path]:
    """The complete release-prose corpus, in stable repository-path order."""

    paths = [repo / "README.md", *(repo / "docs").rglob("*.md")]
    return sorted(paths, key=lambda path: path.relative_to(repo).as_posix())


def _containing_span(position: int, spans: Iterable[tuple[int, int]]) -> bool:
    return any(start <= position < end for start, end in spans)


def _bound_annotations(
    line: int, number: str, annotations: Sequence[Annotation]
) -> list[Annotation]:
    candidate = leading_number(number)
    if candidate is None:
        return []
    bound: list[Annotation] = []
    for annotation in annotations:
        if annotation.is_string:
            continue
        if not annotation.scope_start_line <= line <= annotation.scope_end_line:
            continue
        stated = leading_number(annotation.value)
        if (
            stated is not None
            and agree(stated, candidate, annotation.attrs.get("tol"))[0]
        ):
            bound.append(annotation)
    return bound


def classify_document(path: Path) -> tuple[list[dict[str, Any]], int]:
    """Classify every claim candidate in one Markdown document."""

    payload = path.read_bytes()
    text = payload.decode("utf-8")
    annotations = scan(path)
    fenced_spans = _fenced_spans(text)
    comment_spans = [
        (match.start(), match.end()) for match in ANY_COMMENT.finditer(text)
    ]
    candidates: list[dict[str, Any]] = []

    for match in CLAIM_CANDIDATE.finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        previous_newline = text.rfind("\n", 0, match.start())
        record: dict[str, Any] = {
            "line": line,
            "column": match.start() - previous_newline,
            "literal": match.group(0),
            "number": match.group("number"),
            "unit": match.group("unit"),
        }

        if _containing_span(match.start(), fenced_spans):
            record.update(classification="excluded_context", exclusion="fenced_code")
        elif _containing_span(match.start(), comment_spans):
            record.update(classification="excluded_context", exclusion="html_comment")
        elif (
            match.group("number") == "0"
            and match.group("space") == ""
            and match.group("unit") == "x"
            and match.end() < len(text)
            and text[match.end()] in "0123456789abcdefABCDEF"
        ):
            record.update(
                classification="excluded_context", exclusion="numeric_encoding"
            )
        else:
            bound = _bound_annotations(line, match.group("number"), annotations)
            if bound:
                record.update(
                    classification="provenance_bound",
                    annotation_lines=sorted({annotation.line for annotation in bound}),
                )
            else:
                record["classification"] = "unbound"
        candidates.append(record)

    return candidates, len(annotations)


def _classification_counts(candidates: Sequence[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(candidate["classification"] for candidate in candidates)
    return {
        classification: counts[classification] for classification in CLASSIFICATIONS
    }


def _corpus_digest(documents: Sequence[dict[str, Any]]) -> str:
    """Bind document bytes and their complete candidate classifications."""

    return _sha256(canonical_json(documents))


def build_report(repo: Path = REPO) -> dict[str, Any]:
    documents: list[dict[str, Any]] = []
    total_annotations = 0
    total_candidates = 0
    classification_totals: Counter[str] = Counter()

    for path in corpus_documents(repo):
        relative = path.relative_to(repo).as_posix()
        payload = path.read_bytes()
        candidates, annotation_count = classify_document(path)
        classifications = _classification_counts(candidates)
        total_annotations += annotation_count
        total_candidates += len(candidates)
        classification_totals.update(classifications)
        documents.append(
            {
                "path": relative,
                "sha256": _sha256(payload),
                "counts": {
                    "annotations": annotation_count,
                    "candidates": len(candidates),
                    "classifications": classifications,
                },
                "candidates": candidates,
            }
        )

    totals = {
        "documents": len(documents),
        "zero_candidate_documents": sum(
            document["counts"]["candidates"] == 0 for document in documents
        ),
        "annotations": total_annotations,
        "candidates": total_candidates,
        "classifications": {
            classification: classification_totals[classification]
            for classification in CLASSIFICATIONS
        },
    }
    return {
        "schema": SCHEMA,
        "policy": {
            "corpus": ["README.md", "docs/**/*.md"],
            "candidate_rule": (
                "numeric occurrence followed by one of the evidence-ledger units"
            ),
            "candidate_pattern": CLAIM_CANDIDATE.pattern,
            "units": list(CLAIM_UNITS),
            "classifications": {
                "provenance_bound": (
                    "the candidate agrees with a numeric figure annotation attached "
                    "to the same prose block"
                ),
                "unbound": (
                    "ordinary Markdown prose with no agreeing attached figure annotation"
                ),
                "excluded_context": (
                    "candidate inside fenced code or an HTML comment, or the 0x prefix "
                    "of a numeric encoding; exclusion is recorded"
                ),
            },
            "corpus_digest": "sha256(canonical JSON of the documents array)",
        },
        "corpus_digest": _corpus_digest(documents),
        "totals": totals,
        "documents": documents,
    }


def _resolve_output(repo: Path, output: Path) -> Path:
    return output if output.is_absolute() else repo / output


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO, help=argparse.SUPPRESS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check", action="store_true", help="fail if the checked-in snapshot drifted"
    )
    args = parser.parse_args(argv)

    repo = args.root.resolve()
    output = _resolve_output(repo, args.output)
    payload = canonical_json(build_report(repo))
    if args.check:
        if not output.exists():
            print(
                f"prose figure coverage snapshot is missing: {output}", file=sys.stderr
            )
            return 1
        if output.read_bytes() != payload:
            print(
                "prose figure coverage drift: regenerate "
                f"{output} with {Path(__file__).name}",
                file=sys.stderr,
            )
            return 1
        print(f"prose figure coverage snapshot is current: {output}")
        return 0

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(payload)
    report = json.loads(payload)
    totals = report["totals"]
    print(
        f"wrote {output}: {totals['candidates']} candidates in "
        f"{totals['documents']} documents; "
        f"{totals['classifications']['unbound']} unbound"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
