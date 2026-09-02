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
DEFAULT_TRIAGE_POLICY = Path("configs/evidence/prose_figure_triage.json")

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

SCHEMA = "opentallas.prose_figure_coverage.v2"
TRIAGE_SCHEMA = "opentallas.prose_figure_triage_policy.v1"
CLASSIFICATIONS = ("provenance_bound", "unbound", "excluded_context")
TRIAGE_DISPOSITIONS = (
    "produced",
    "external",
    "normative_or_example",
    "missing_producer",
    "untriaged",
)
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


def _heading_paths(text: str, fenced_spans: Sequence[tuple[int, int]]) -> dict[int, list[str]]:
    """Return the live Markdown heading stack at each source line.

    Headings inside fenced examples are ignored.  The path is evidence useful
    to a reviewer and is also a more durable triage selector than a line
    number.
    """

    paths: dict[int, list[str]] = {}
    stack: list[str] = []
    offset = 0
    for line_number, line in enumerate(text.splitlines(keepends=True), start=1):
        if not _containing_span(offset, fenced_spans):
            match = re.match(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$", line.rstrip("\r\n"))
            if match:
                level = len(match.group(1))
                stack = stack[: level - 1]
                stack.append(match.group(2).strip())
        paths[line_number] = list(stack)
        offset += len(line)
    return paths


def _read_triage_policy(repo: Path, policy_path: Path) -> tuple[dict[str, Any], bytes | None, str]:
    """Read and structurally validate the explicit unbound-figure policy."""

    resolved = policy_path if policy_path.is_absolute() else repo / policy_path
    relative = (
        resolved.relative_to(repo).as_posix()
        if resolved.is_relative_to(repo)
        else str(resolved)
    )
    if not resolved.exists():
        if repo.resolve() == REPO.resolve():
            raise ValueError(f"canonical triage policy is missing: {relative}")
        return {"schema": TRIAGE_SCHEMA, "rules": []}, None, relative
    payload = resolved.read_bytes()
    try:
        policy = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"triage policy {relative} is not valid JSON: {exc}") from exc
    if not isinstance(policy, dict) or policy.get("schema") != TRIAGE_SCHEMA:
        raise ValueError(f"triage policy {relative} must use schema {TRIAGE_SCHEMA}")
    rules = policy.get("rules")
    if not isinstance(rules, list):
        raise ValueError(f"triage policy {relative}.rules must be a JSON array")
    seen: set[str] = set()
    for index, rule in enumerate(rules):
        label = f"triage policy {relative}.rules[{index}]"
        if not isinstance(rule, dict):
            raise ValueError(f"{label} must be a JSON object")
        rule_id = rule.get("id")
        if not isinstance(rule_id, str) or not rule_id:
            raise ValueError(f"{label}.id must be a nonempty string")
        if rule_id in seen:
            raise ValueError(f"triage policy {relative} repeats rule id {rule_id!r}")
        seen.add(rule_id)
        if rule.get("disposition") not in TRIAGE_DISPOSITIONS[:-1]:
            raise ValueError(f"{label}.disposition is not an allowed resolved class")
        if not isinstance(rule.get("rationale"), str) or not rule["rationale"].strip():
            raise ValueError(f"{label}.rationale must be nonempty")
        expected = rule.get("expected_matches")
        if not isinstance(expected, int) or isinstance(expected, bool) or expected <= 0:
            raise ValueError(f"{label}.expected_matches must be a positive integer")
        match = rule.get("match")
        if not isinstance(match, dict) or not isinstance(match.get("path"), str):
            raise ValueError(f"{label}.match.path must be an exact document path")
        unknown = set(match) - {
            "path",
            "heading_contains",
            "literal",
            "unit",
            "line_contains",
        }
        if unknown:
            raise ValueError(f"{label}.match has unknown selectors: {sorted(unknown)}")
        for field, value in match.items():
            if not isinstance(value, str) or not value:
                raise ValueError(f"{label}.match.{field} must be a nonempty string")
        if rule["disposition"] == "produced" and (
            not isinstance(rule.get("producer"), str)
            or not rule["producer"].strip()
        ):
            raise ValueError(f"{label}.producer is required for produced figures")
        if rule["disposition"] == "external" and (
            not isinstance(rule.get("source"), str) or not rule["source"].strip()
        ):
            raise ValueError(f"{label}.source is required for external figures")
    return policy, payload, relative


def _triage_rule_matches(
    rule: dict[str, Any], path: str, candidate: dict[str, Any]
) -> bool:
    match = rule["match"]
    if path != match["path"]:
        return False
    if "literal" in match and candidate["literal"] != match["literal"]:
        return False
    if "unit" in match and candidate["unit"] != match["unit"]:
        return False
    if "heading_contains" in match and not any(
        match["heading_contains"] in heading for heading in candidate["heading_path"]
    ):
        return False
    if "line_contains" in match and match["line_contains"] not in candidate["_line_text"]:
        return False
    return True


def _triage_unbound_candidates(
    documents: Sequence[dict[str, Any]], rules: Sequence[dict[str, Any]]
) -> Counter[str]:
    """Apply only explicit rules and fail on ambiguity or stale selectors."""

    use_count: Counter[str] = Counter()
    dispositions: Counter[str] = Counter()
    for document in documents:
        for candidate in document["candidates"]:
            if candidate["classification"] != "unbound":
                candidate.pop("_line_text", None)
                continue
            matches = [
                rule
                for rule in rules
                if _triage_rule_matches(rule, document["path"], candidate)
            ]
            if len(matches) > 1:
                ids = [rule["id"] for rule in matches]
                raise ValueError(
                    f"ambiguous prose triage at {document['path']}:"
                    f"{candidate['line']} {candidate['literal']!r}: {ids}"
                )
            if not matches:
                candidate["triage"] = {"disposition": "untriaged"}
                dispositions["untriaged"] += 1
            else:
                rule = matches[0]
                use_count[rule["id"]] += 1
                triage = {
                    "disposition": rule["disposition"],
                    "rule": rule["id"],
                    "rationale": rule["rationale"],
                }
                if "producer" in rule:
                    triage["producer"] = rule["producer"]
                if "source" in rule:
                    triage["source"] = rule["source"]
                candidate["triage"] = triage
                dispositions[rule["disposition"]] += 1
            candidate.pop("_line_text", None)
    for rule in rules:
        actual = use_count[rule["id"]]
        expected = rule["expected_matches"]
        if actual != expected:
            raise ValueError(
                f"triage rule {rule['id']!r} matched {actual} candidates; "
                f"expected {expected}"
            )
    return dispositions


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
    source_lines = text.splitlines()
    annotations = scan(path)
    fenced_spans = _fenced_spans(text)
    heading_paths = _heading_paths(text, fenced_spans)
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
            "heading_path": heading_paths.get(line, []),
            "_line_text": source_lines[line - 1],
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


def build_report(
    repo: Path = REPO, triage_policy_path: Path = DEFAULT_TRIAGE_POLICY
) -> dict[str, Any]:
    triage_policy, triage_payload, triage_relative = _read_triage_policy(
        repo, triage_policy_path
    )
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

    triage_totals = _triage_unbound_candidates(documents, triage_policy["rules"])

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
        "unbound_triage": {
            disposition: triage_totals[disposition]
            for disposition in TRIAGE_DISPOSITIONS
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
            "unbound_triage": {
                "produced": "a known producer exists but the figure still lacks a resolving annotation",
                "external": "an externally sourced value, with the source named by its triage rule",
                "normative_or_example": "a contract value, algebraic notation, or worked example rather than an empirical result",
                "missing_producer": "a load-bearing result for which no machine-readable producer is known",
                "untriaged": "not yet reviewed; no evidence claim is made",
            },
            "corpus_digest": "sha256(canonical JSON of the documents array)",
        },
        "triage_policy": {
            "path": triage_relative,
            "sha256": _sha256(triage_payload) if triage_payload is not None else None,
            "schema": TRIAGE_SCHEMA,
            "rule_count": len(triage_policy["rules"]),
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
    parser.add_argument("--triage-policy", type=Path, default=DEFAULT_TRIAGE_POLICY)
    parser.add_argument(
        "--check", action="store_true", help="fail if the checked-in snapshot drifted"
    )
    args = parser.parse_args(argv)

    repo = args.root.resolve()
    output = _resolve_output(repo, args.output)
    payload = canonical_json(build_report(repo, args.triage_policy))
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
        f"{totals['classifications']['unbound']} unbound, "
        f"{totals['unbound_triage']['untriaged']} untriaged"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
