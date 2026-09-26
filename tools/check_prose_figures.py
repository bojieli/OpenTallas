#!/usr/bin/env python3
"""Refuse a number in prose that no longer matches the artifact that produces it.

`tools/check_evidence_grades.py` guards 151 graded entries in one JSON file.
Nothing read a number in a `.md` file until this existed. On 2026-08-30 the
headline moved from 54.2x to 8.6x across six independent corrections; every
generated artifact was regenerated and every document quoting an intermediate
value silently became wrong. The audit in `docs/EVIDENCE_LEDGER.md` found 80 of
108 load-bearing figures stale, and named the mechanism rather than the
incident:

    The documents that cite artifacts had their errors caught and retracted;
    the ones that cite nothing still carry them live.

So this checker does not lint prose. It reads a machine-resolvable provenance
annotation that an author attaches to a figure, re-reads the artifact, and fails
when the two disagree.

THE ANNOTATION
--------------

One HTML comment. Invisible in every renderer, greppable, and diffable:

    <!-- figure: 35.3358 src="results/model-traffic/sweep.csv#weight_to_kv_read_ratio"
         where="model=DeepSeek-V4-Flash-0731;context_tokens=200000;batch_size=1" -->

    <!-- figure: 35.335 src="results/abi3/deepseek_v4_reference_oracle_context_ladder.json#context_ladder_summary.rungs[4].weight_to_kv_read_ratio_at_this_context" -->

    <!-- figure: 9.50 src="results/roofline/n6_vs_a100/REPORT.md#Ratio after"
         table="latency separation" where="Model=DeepSeek-V4-Flash-0731;mm2=554700" -->

Grammar:

    figure: <value> src="<path>#<selector>" [where="k=v;k=v"] [table="<heading>"]
            [tol="<n>|<n>%|exact"] [scale="<n>"] [name="<label>"]

    <value>    what the prose says. Bare = numeric; "quoted" = an exact string
               (a graph id, a status, a hash). A quoted value ending in `...` or
               an ellipsis is a prefix match, for the truncated digests prose
               actually prints.
    src        repo-relative path, `#`, then a selector:
                 *.json  a dotted path: `a.b[4].c`, `a["key with spaces"]`, or
                         `rungs[workload=TA-DS-CTX-200K-1].field`, which picks
                         one entry of a list by one or more comma-separated
                         field values and survives a reordering an index does
                         not
                 *.csv   a column name; `where` picks the row
                 *.md    a column name of a GFM table; `where` picks the row
    where      row selector, `column=value` pairs separated by `;`. Values are
               matched textually, or numerically when both sides are pure
               numbers -- so `mm2=554700` finds the cell `554,700`. The
               selection must be unique or the check fails as ambiguous.
    table      substring of the heading a markdown table sits under, when a
               column name occurs in more than one table of the same file.
    tol        loosens the default tolerance; see below. Never tightens it,
               except `tol="exact"`, which demands equality.
    scale      one multiplicative constant applied to the artifact value before
               comparison -- for GB against bytes, or % against a fraction.
               Deliberately not an expression: an annotation must not become a
               second, unchecked derivation.
    name       a label for the failure message. Optional, and worth writing.

LINE NUMBERS ARE FORBIDDEN, deliberately. The audit found the ledger's own
`FILE.md:52` references had already drifted while the values they pointed at
still held. A selector that survives an edit above it is the whole point.

WHAT IT COMPARES, AND HOW STRICTLY
----------------------------------

Two comparisons, both of which must hold. The first is freshness; the second is
what stops the annotation from drifting away from the number it labels.

  1. annotated value  <->  artifact value.
  2. annotated value  <->  the numbers in the prose it is attached to.

An annotation attaches to a SCOPE, by adjacency rather than by line number: if
the comment shares a line with other text -- as it does when trailing a table
row -- the scope is that line; otherwise it is the next non-blank block. If the
value the annotation carries is not among the numbers in its scope, the check
fails: somebody edited the prose and not the annotation.

TOLERANCE is explicit, and it is a statement about written precision rather
than a fudge factor:

    Two numbers agree when they differ by no more than half of the coarser of
    the two written precisions.

`35.3` is written to 0.1, so it admits +-0.05: `35.3`, `35.30`, `35.3:1` and an
artifact's `35.33578981` all agree, and `36.1` does not. `13,063` is written to
1, so an artifact's `13,063.4` agrees and `13,100` does not. This is what makes
the checker tolerant of formatting and strict about value, and it needs no
per-figure configuration in the common case. A figure deliberately quoted as a
band -- `~9,000 tok/s` against an artifact's `9,018.8` -- says so with
`tol="1%"`.

WHAT IT IS SILENT ABOUT
-----------------------

Every number nobody annotated. That is a design choice, not an omission: a
checker that flags every year, version string and worked example is one nobody
runs, and the repository already has two such lessons. The cost is that
coverage is a human judgement, so `REQUIRED_COVERAGE` below pins a floor per
document -- annotations can be added freely, but not silently deleted.

ITS STATED BLIND SPOT: FIGURES NOTHING PRODUCES
-----------------------------------------------

A figure can only be checked against a producer. The audit found load-bearing
figures that are asserted in prose and emitted by no script, artifact or test.
They CANNOT be annotated, this checker cannot see them, and they are the next
numbers to rot. Naming them is the durable part. They are not all the same
shape, and the shape decides what would fix them.

(a) Genuinely computed by nothing. These are the real blind spot:

  * `84.7%` / `87.0%`  index share of the KV read
    (a legacy analytical report, deleted 2026-09-23). The arithmetic is right --
    21 x 50,000 x 256 B of 317,435,904 B -- and it is in no artifact. A grep for
    `84.7%` across `results/`, `configs/`, `src/` and `tools/` returns nothing.
  * `290.4 ns` per compressed-sparse layer -- CORRECTION to the audit: this one
    IS produced, at `results/roofline/*/analytical.json` ->
    `model_summaries[model=...].layer_fixed_latency.seconds_per_compressed_sparse_layer`
    = 2.904111536354303e-07. It is annotatable and should be annotated. The
    fixed-latency share table beside it -- `55.4 / 38.7 / 34.7 / 6.6 / 2.0 /
    0.9%` -- is not.
  * `11,747 feasible points`. It LOOKS produced -- it appears in
    `results/roofline/n6_vs_a100/REPORT.md` -- but it is a hard-coded string
    literal at `tools/run_roofline_studies.py:3154` inside an otherwise
    f-string finding. A number that a generator prints without computing is
    worse than one with no producer, because its home makes it look checked.
    The same is true of `46,225 mm2 wafer`, `681 reticle fields`, `1.4x` and
    the watts `54.2 / 27.0 / 85.3 W` elsewhere in that file.
  * `0.181 / 0.851 / 1.340 / 1.684 W/mm2` and `339 / 581 / 987`; `1.02x to
    3.14x` over `125 GPU points`; `3.69 devices engaged, 2.53 effective,
    1.46x`; and the whole per-user results table `216 / 229 / 4,022 / 1,143 /
    ...`, which is sourced to a report table that carries aggregate only.
  * `100.4 mm2 of an 815 mm2 die at N6`
    (`docs/UNIFIED_EXECUTION_CHECKLIST.md`). `grep -rn "100.4 mm" results/` is
    empty. The byte figure beside it, 1,207,959,552 B, IS produced.
  * "all 27 distinct prefill kernels diffed kernel-by-kernel through the
    `on_issue` hook: bit-identical" -- graded `executed` with no artifact to
    execute and no tool named.
  * `1.4 us`, "the measured speed-of-light all-reduce floor on GB200" -- graded
    `measured` with no source, sitting between two properly cited papers.
  * The wafer is `8.3x` cheaper on Flash and `8.9x` on Pro. The artifact states
    only "at least 2.0x"; the per-model split is in neither study report.
  * `299 mm2` MAC-array area recovered, `0.41x` feed fraction, and "the mean
    understates the sweep by 1.6x to 2.7x" -- asserted inside
    `src/opentallas/roofline.py`, computed by nothing.
  * `15.137 GB` Qwen weight read per token, and the W:KV ratios that descend
    from it at 1,024 and 32,768 tokens. `results/model-traffic/sweep.csv` has
    no Qwen row and the roofline model summaries carry only the 8,192 rung, so
    two of the three Qwen rows of a legacy report's §2 (deleted 2026-09-23)
    have no artifact at all -- they are the output of the shell command in that
    document's header, which writes nothing down.
  * Whole documents: `docs/METHODOLOGY.md` (9). A legacy report with 16
    such figures was deleted on 2026-09-23. The SHA-256 digests across the 16
    `docs/DEEPSEEK_V4_*_EVIDENCE.md` files name no reproduction command.

(b) Config inputs echoed back by the generator that consumed them. These
    resolve, and this checker will happily check them -- but the check is
    circular, and what is actually missing is an external source:

  * `16,960 tok/s`  Taalas HC1 per user, the validation gate for the whole
    model. `configs/hardware/technology.json` ->
    `reference_parts.taalas_hc1.published_tokens_s_per_user` states it and both
    roofline reports echo it in their gate table. Its evidence is three
    secondary press reports, and `docs/SOURCES.md` had no row for "Taalas" or
    "HC1" at all until 2026-08-30 -- while `SOURCES.md` itself forbids
    secondary press for a value. Annotated here, with that caveat named.
  * `46,225 mm2`  WSE-2 wafer area, the numerator of the N7 compute roof.
    `technology.json -> wafer.area_mm2`, echoed as the `mm2` column of the
    iso-area tables. `SRC-CEREBRAS-WSE2` carries no URL, no date and no hash,
    where its sibling `SRC-CEREBRAS-WSE3` carries all three.
  * `823 mm2` GC200 die and `47.5 TB/s`, the denominator of that same roof.
    `configs/hardware/technology_inputs.json -> graphcore_gc200`, and echoed by
    no report at all. `SRC-GC200`, second sentence: "Public GC200 architecture
    disclosures", no URL.
  * `60 GB/s/mm2` (YOLoC) and `20.7 MB/mm2` (3D-METRO), the two most
    load-bearing ROM constants. DOIs present; `SOURCES.md` discloses that both
    resolvers returned HTTP 403 and claims no content validation.

Do not invent a producer for one of these to make it annotatable. Either
something computes it and writes it down, or the honest annotation is the
absence of one.

ITS SECOND BLIND SPOT: A FRESH NUMBER THAT MEANS SOMETHING ELSE
---------------------------------------------------------------

Everything above is about a figure drifting from its artifact. This checker
closes that. It cannot close the other half, and one class of figure in this
repository is quoted all night in a way the artifact does not support.

**A retired-instruction count measures reach, not fidelity.** An execution
record's `instructions.retired` says how far a program got before it trapped:
`N instructions issued and retired without a trap`. It does not say
`the first N operations of the model were computed`, and the two are different
claims about different things. Arithmetic that is wrong but finite does not
trap -- it produces a number and execution continues -- so a lane can retire
more instructions *because* a defect let it past a check, and the count will
rise exactly as it does when a defect is fixed.

That is not hypothetical. On 2026-08-30 the HBM lane was found to be addressing
791 of 795 block-scaled weights from the wrong codes and dropping all 427
quantised-activation scales entirely; every retired count it had reported --
251, 299, 1,896 -- was real as a progress marker and described execution
through FP8 and MXFP4 contractions that were not computing at the released
checkpoint's precision. No published figure had to be retracted, because none
had ever been offered as evidence of correctness; but the distinction was never
drawn either, and prose that says "the lane computes the first N operations"
would have been false while every annotation in it resolved.

So, when annotating one of these:

  * `retired`, `retired_work`, `instructions.retired` -- name what they are.
    `name="DeepSeek HBM retired"` is right; a label implying computation is
    not. The prose beside them should say `retires N instructions` and not
    `computes N operations`.
  * The only figure that carries fidelity is a token compared against a
    reference: `reference_agreement`, `first_divergence_index`, and the token
    ids themselves. Annotate those where a correctness claim is being made,
    and prefer them to any count.
  * A count rising is evidence a wall moved. It is not evidence the work
    before the wall was right. Those need separate artifacts and separate
    annotations, and this checker will not notice if you conflate them.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

REPO = Path(__file__).resolve().parents[1]

#: Documents whose annotations must not silently disappear. A floor, not a
#: target: raise it when you annotate more. The audit's finding was structural
#: -- provenance is what made the difference between a caught error and a live
#: one -- so every document that currently publishes checked figures belongs in
#: this map. Otherwise a whole evidence section can quietly lose its annotations
#: while the aggregate checker remains green.
REQUIRED_COVERAGE: dict[str, int] = {
    "README.md": 8,
    "docs/ABI3_ENGINE_DATAPATH_RTL.md": 67,
    "docs/ABI3_PROGRAM_REPORT.md": 17,
    "docs/ANALYTICAL_REPORT.md": 142,
    "docs/CHIP_ARCHITECTURE_DESIGN.md": 19,
    "docs/DEEPSEEK_SPARSE_ATTENTION_GATE.md": 55,
    "docs/DFT.md": 92,
    "docs/DEEPSEEK_V41_FLASH_ROM_IMPLEMENTATION_PLAN.md": 14,
    "docs/DEEPSEEK_V4_ROM_ARRAY_IMPLEMENTATION_PLAN.md": 9,
    "docs/EVIDENCE_LEDGER.md": 44,
    "docs/HOST_INTERFACE_AND_RUNTIME.md": 15,
    "docs/FOUR_TARGET_IMPLEMENTATION_MASTER_PLAN.md": 2,
    "docs/OVERVIEW.md": 6,
    "docs/ROM_DENSITY_NODE_TRANSFER.md": 24,
    "docs/ROM_PHYSICAL_METHODOLOGY.md": 64,
    "docs/ROM_SERVICE_RTL.md": 40,
    "docs/SOURCES.md": 6,
    "docs/TENSOR_ACCELERATOR_ABI_3_ARCHITECTURE_DECISION.md": 2,
    "docs/TOKEN_PIPELINE_OPTIMIZATION_PLAN.md": 56,
    "docs/UNIFIED_EXECUTION_CHECKLIST.md": 245,
    "docs/VISION.md": 1,
    "docs/WAFER_VS_ARRAY_ISO_AREA.md": 17,
}

ANNOTATION = re.compile(r"<!--\s*figure:\s*(?P<body>.*?)-->", re.S)
ANY_COMMENT = re.compile(r"<!--.*?-->", re.S)
FENCE = re.compile(r"^\s*(```|~~~)")
HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(?P<title>.*?)\s*#*\s*$")
#: A written number: optional sign, thousands separators, optional fraction,
#: optional exponent. `35.3`, `-1,234`, `1.764e+11`.
NUMBER = re.compile(r"[-+]?\d[\d,_]*(?:\.\d+)?(?:[eE][-+]?\d+)?")
PURE_NUMBER = re.compile(r"^[-+]?\d[\d,_]*(?:\.\d+)?(?:[eE][-+]?\d+)?$")
TOKEN = re.compile(
    r"""\s*(?:(?P<key>[A-Za-z_][\w-]*)\s*=\s*)?"""
    r"""(?:"(?P<dq>[^"]*)"|'(?P<sq>[^']*)'|(?P<bare>\S+))"""
)
KNOWN_KEYS = {"src", "where", "table", "tol", "scale", "name", "why"}
#: Markdown decoration that changes how a cell looks and not what it says.
DECORATION = re.compile(r"(\*\*|__|~~|`|\*|_)")


class AnnotationError(Exception):
    """The annotation itself is malformed or unresolvable."""


# --------------------------------------------------------------------------
# numbers


@dataclass(frozen=True)
class Quantity:
    """A number, and the precision it was written to."""

    value: float
    quantum: float
    literal: str

    def __str__(self) -> str:
        return self.literal


def _quantum(literal: str) -> float:
    """The magnitude of the last written digit. `35.3` -> 0.1, `13,063` -> 1."""

    lit = literal.replace(",", "").replace("_", "")
    mantissa, _, exponent = lit.lower().partition("e")
    scale = int(exponent) if exponent else 0
    decimals = len(mantissa.split(".", 1)[1]) if "." in mantissa else 0
    return 10.0 ** (scale - decimals)


def _to_quantity(literal: str) -> Quantity:
    return Quantity(float(literal.replace(",", "").replace("_", "")),
                    _quantum(literal), literal)


def leading_number(text: str) -> Quantity | None:
    """The first number in a cell, ignoring whatever unit follows it."""

    match = NUMBER.search(clean(text))
    return _to_quantity(match.group(0)) if match else None


def pure_number(text: str) -> Quantity | None:
    """A number only if the whole string is one. `NVIDIA-B300-x16` is not."""

    stripped = clean(text)
    return _to_quantity(stripped) if PURE_NUMBER.match(stripped) else None


def numbers_in(text: str) -> list[Quantity]:
    return [_to_quantity(m.group(0)) for m in NUMBER.finditer(text)]


def clean(text: str) -> str:
    """Strip markdown decoration and embedded comments; keep the words."""

    return DECORATION.sub("", ANY_COMMENT.sub("", str(text))).strip()


def explicit_tolerance(tol: str, reference: float) -> float:
    tol = tol.strip()
    if tol.endswith("%"):
        return abs(reference) * float(tol[:-1]) / 100.0
    return abs(float(tol))


def agree(stated: Quantity, produced: Quantity, tol: str | None) -> tuple[bool, float]:
    """Half of the coarser written precision, or an explicit tolerance.

    Documented in the module docstring and enforced nowhere else, so that the
    rule a reader is told is the rule that runs.
    """

    if tol is not None and tol.strip().lower() == "exact":
        allowed = 0.0
    else:
        allowed = 0.5 * max(stated.quantum, produced.quantum)
        if tol is not None:
            allowed = max(allowed, explicit_tolerance(tol, produced.value))
    return abs(stated.value - produced.value) <= allowed * (1 + 1e-9) + 1e-12, allowed


# --------------------------------------------------------------------------
# annotations


@dataclass
class Annotation:
    document: Path
    line: int
    value: str
    is_string: bool
    attrs: dict[str, str]
    scope: str
    raw: str
    scope_start_line: int = 0
    scope_end_line: int = 0

    @property
    def label(self) -> str:
        return self.attrs.get("name") or self.attrs.get("src", "?")

    @property
    def shown(self) -> str:
        path = self.document.resolve()
        rel = path.relative_to(REPO) if path.is_relative_to(REPO) else path
        return f"{rel}:{self.line}"


def parse_body(body: str) -> tuple[str, bool, dict[str, str]]:
    attrs: dict[str, str] = {}
    value: str | None = None
    is_string = False
    position = 0
    while position < len(body):
        match = TOKEN.match(body, position)
        if not match:
            break
        position = match.end()
        raw = match.group("dq") if match.group("dq") is not None else (
            match.group("sq") if match.group("sq") is not None else match.group("bare"))
        key = match.group("key")
        if key is None:
            if value is not None:
                raise AnnotationError(
                    f"two positional values ({value!r} then {raw!r}); everything "
                    "after the figure's own value must be key=\"value\"")
            value = raw
            is_string = match.group("dq") is not None or match.group("sq") is not None
        else:
            if key not in KNOWN_KEYS:
                raise AnnotationError(
                    f"unknown attribute {key!r}. Known: {sorted(KNOWN_KEYS)}. A typo "
                    "must not quietly disable a check.")
            attrs[key] = raw
    if value is None:
        raise AnnotationError("no value: write `figure: <the number the prose states>`")
    if "src" not in attrs:
        raise AnnotationError("no src=; a figure with no producer cannot be checked")
    return value, is_string, attrs


def _blank_comments(text: str) -> str:
    """Remove comments while preserving the line structure around them."""

    return ANY_COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), text)


def _fenced_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    offset = 0
    start: int | None = None
    for line in text.splitlines(keepends=True):
        if FENCE.match(line):
            if start is None:
                start = offset
            else:
                spans.append((start, offset + len(line)))
                start = None
        offset += len(line)
    if start is not None:
        spans.append((start, offset))
    return spans


def scan(document: Path, max_block_lines: int = 60) -> list[Annotation]:
    """Every annotation in a document, with the prose each one attaches to."""

    text = document.read_text()
    fenced = _fenced_spans(text)
    stripped = _blank_comments(text).splitlines()
    found: list[Annotation] = []

    for match in ANNOTATION.finditer(text):
        if any(a <= match.start() < b for a, b in fenced):
            continue
        first = text.count("\n", 0, match.start())
        last = text.count("\n", 0, match.end())

        own = " ".join(
            stripped[i].strip() for i in range(first, min(last, len(stripped) - 1) + 1)
            if i < len(stripped) and stripped[i].strip()
        )
        if own:
            scope = own
            scope_start_line = first + 1
            scope_end_line = min(last, len(stripped) - 1) + 1
        else:
            index = last + 1
            while index < len(stripped) and not stripped[index].strip():
                index += 1
            scope_start_line = index + 1
            block: list[str] = []
            while (index < len(stripped) and stripped[index].strip()
                   and len(block) < max_block_lines):
                block.append(stripped[index].strip())
                index += 1
            scope = " ".join(block)
            scope_end_line = index

        value, is_string, attrs = parse_body(match.group("body"))
        found.append(Annotation(document=document, line=first + 1, value=value,
                                is_string=is_string, attrs=attrs, scope=scope,
                                raw=match.group(0),
                                scope_start_line=scope_start_line,
                                scope_end_line=scope_end_line))
    return found


# --------------------------------------------------------------------------
# artifacts


#: One document can annotate fifty figures against one report. Parse each
#: artifact once.
_ARTIFACT_CACHE: dict[Path, Any] = {}


def _cached(path: Path, parse):
    if path not in _ARTIFACT_CACHE:
        _ARTIFACT_CACHE[path] = parse(path)
    return _ARTIFACT_CACHE[path]


@dataclass
class Table:
    section: str
    columns: list[str]
    rows: list[dict[str, str]]


def parse_markdown_tables(text: str) -> list[Table]:
    lines = text.splitlines()
    tables: list[Table] = []
    section = ""
    index = 0
    while index < len(lines):
        heading = HEADING.match(lines[index])
        if heading:
            section = heading.group("title")
            index += 1
            continue
        if (lines[index].lstrip().startswith("|") and index + 1 < len(lines)
                and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[index + 1])):
            columns = _cells(lines[index])
            rows: list[dict[str, str]] = []
            index += 2
            while index < len(lines) and lines[index].lstrip().startswith("|"):
                cells = _cells(lines[index])
                rows.append({name: (cells[i] if i < len(cells) else "")
                             for i, name in enumerate(columns)})
                index += 1
            tables.append(Table(section=section, columns=columns, rows=rows))
            continue
        index += 1
    return tables


def _cells(line: str) -> list[str]:
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|"):
        body = body[:-1]
    return [clean(cell) for cell in body.split("|")]


def parse_where(where: str | None) -> list[tuple[str, str]]:
    if not where:
        return []
    pairs = []
    for clause in where.split(";"):
        clause = clause.strip()
        if not clause:
            continue
        if "=" not in clause:
            raise AnnotationError(
                f"where clause {clause!r} is not `column=value`; separate pairs with ;")
        column, _, wanted = clause.partition("=")
        pairs.append((column.strip(), wanted.strip()))
    return pairs


def cell_matches(cell: str, wanted: str) -> bool:
    if clean(cell) == clean(wanted):
        return True
    left, right = pure_number(cell), pure_number(wanted)
    if left is not None and right is not None:
        return agree(right, left, None)[0]
    return False


def _select_rows(rows: Iterable[dict[str, str]],
                 pairs: Sequence[tuple[str, str]]) -> list[dict[str, str]]:
    return [row for row in rows
            if all(key in row and cell_matches(row[key], want) for key, want in pairs)]


JSON_STEP = re.compile(
    r"""\[\s*(?:(\d+)|"([^"]*)"|'([^']*)'|(?P<pred>[^\]]*=[^\]]*))\s*\]|([^.\[\]]+)""")


def resolve_json(body: Any, selector: str, where: str) -> Any:
    """Walk `a.b[4].c`, `a["key with spaces"]`, or `a[name=thing].c`.

    The predicate form picks one entry of a list of objects by a field value,
    which survives a reordering of the list where an index does not. Prefer it.
    """

    node: Any = body
    trail = ""
    for step in JSON_STEP.finditer(selector):
        index, dq, sq, predicate, key = (
            step.group(1), step.group(2), step.group(3),
            step.group("pred"), step.group(5))
        if predicate is not None:
            trail += f"[{predicate}]"
            conditions = []
            for clause in predicate.split(","):
                field, _, wanted = clause.partition("=")
                conditions.append((field.strip(), wanted.strip()))
            if not isinstance(node, list):
                raise AnnotationError(
                    f"{where}: {trail} selects in a {type(node).__name__}, not a list")
            hits = [item for item in node
                    if isinstance(item, dict)
                    and all(field in item and cell_matches(str(item[field]), wanted)
                            for field, wanted in conditions)]
            if len(hits) != 1:
                raise AnnotationError(
                    f"{where}: {trail} selects {len(hits)} of {len(node)} entries; "
                    "a figure must resolve to exactly one")
            node = hits[0]
            continue
        if index is not None:
            trail += f"[{index}]"
            if not isinstance(node, list):
                raise AnnotationError(f"{where}: {trail} indexes a {type(node).__name__}")
            position = int(index)
            if position >= len(node):
                raise AnnotationError(
                    f"{where}: {trail} is out of range; the list has {len(node)} entries")
            node = node[position]
            continue
        name = dq if dq is not None else (sq if sq is not None else (key or "").strip())
        trail += f".{name}"
        if not isinstance(node, dict) or name not in node:
            available = sorted(node)[:12] if isinstance(node, dict) else type(node).__name__
            raise AnnotationError(f"{where}: {trail} does not exist; found {available}")
        node = node[name]
    return node


@dataclass
class Resolved:
    text: str
    detail: str


def resolve(annotation: Annotation) -> Resolved:
    src = annotation.attrs["src"]
    if "#" not in src:
        raise AnnotationError(
            f"src={src!r} names a file but no field. Write path#selector -- a JSON "
            "path, or a column name for a csv or markdown table.")
    relative, _, selector = src.rpartition("#")
    path = REPO / relative
    if not path.is_file():
        raise AnnotationError(f"src={src!r}: {relative} is not in the repository")
    pairs = parse_where(annotation.attrs.get("where"))
    where_shown = annotation.attrs.get("where", "")

    if path.suffix == ".json":
        if pairs:
            raise AnnotationError("where= is for csv and markdown rows; a JSON "
                                  "selector addresses the field directly")
        body = _cached(path, lambda p: json.loads(p.read_text()))
        value = resolve_json(body, selector, relative)
        if isinstance(value, (dict, list)):
            raise AnnotationError(
                f"{relative}#{selector} is a {type(value).__name__}, not a value")
        return Resolved(text=str(value), detail=f"{relative} -> {selector}")

    if path.suffix == ".csv":
        rows = _cached(path, lambda p: list(csv.DictReader(p.open(newline=""))))
        if not rows or selector not in rows[0]:
            raise AnnotationError(
                f"{relative} has no column {selector!r}; it has "
                f"{sorted(rows[0]) if rows else 'no rows'}")
        picked = _select_rows(rows, pairs)
        if len(picked) != 1:
            raise AnnotationError(
                f"{relative}: where={where_shown!r} selects {len(picked)} rows of "
                f"{len(rows)}; a figure must resolve to exactly one")
        return Resolved(text=picked[0][selector],
                        detail=f"{relative} row {where_shown} col {selector!r}")

    if path.suffix in {".md", ".markdown"}:
        tables = _cached(path, lambda p: parse_markdown_tables(p.read_text()))
        wanted_table = annotation.attrs.get("table")
        if wanted_table:
            tables = [t for t in tables
                      if wanted_table.lower() in t.section.lower()]
            if not tables:
                raise AnnotationError(
                    f"{relative}: no table under a heading matching {wanted_table!r}")
        hits: list[tuple[Table, dict[str, str]]] = []
        for table in tables:
            if selector not in table.columns:
                continue
            for row in _select_rows(table.rows, pairs):
                hits.append((table, row))
        if len(hits) != 1:
            sections = sorted({t.section for t, _ in hits})
            raise AnnotationError(
                f"{relative}: column {selector!r} with where={where_shown!r} selects "
                f"{len(hits)} rows"
                + (f" across {sections}; add table=\"...\" to disambiguate"
                   if len(hits) > 1 else
                   ". Check the column name and the row key against the file."))
        table, row = hits[0]
        return Resolved(text=row[selector],
                        detail=f"{relative} §{table.section!r} row {where_shown} "
                               f"col {selector!r}")

    raise AnnotationError(
        f"src={src!r}: {path.suffix or 'that'} is not a readable artifact kind "
        "(.json, .csv, .md)")


# --------------------------------------------------------------------------
# checking


@dataclass
class Finding:
    annotation: Annotation
    headline: str
    lines: list[str]

    def render(self) -> str:
        body = "\n".join(f"      {line}" for line in self.lines)
        return f"  {self.annotation.shown}  {self.headline}\n{body}"


#: Artifacts under ``build/`` are BUILD PRODUCTS: .gitignore excludes them, so a
#: fresh clone does not have them and a figure bound to one cannot be resolved
#: there.  Before this exemption the checker passed for anyone who had already
#: built and failed for everyone else -- which is precisely backwards for a
#: reproducibility check, and made `make check-figures` unusable in CI.
#:
#: Such a figure is reported as UNVERIFIABLE-HERE rather than silently skipped or
#: counted as a pass: the annotation is still wrong to have, because a published
#: figure should cite evidence a reader can obtain.  The right fix is to bind it
#: to a tracked artifact under results/, or to retract the figure.
BUILD_PRODUCT_PREFIX = "build/"


def annotation_needs_a_build(annotation: Annotation) -> bool:
    return str(annotation.attrs.get("src", "")).startswith(BUILD_PRODUCT_PREFIX)


def check_annotation(annotation: Annotation) -> Finding | None:
    try:
        resolved = resolve(annotation)
    except AnnotationError as error:
        if annotation_needs_a_build(annotation) and not (
            REPO / str(annotation.attrs["src"]).split("#", 1)[0]
        ).exists():
            # Unbuilt tree: not this checker's failure to report.  The caller
            # counts these separately and says so.
            return None
        return Finding(annotation, f"unresolvable provenance for {annotation.label!r}",
                       [str(error)])

    stated_text = clean(annotation.value)
    scale = float(annotation.attrs["scale"]) if "scale" in annotation.attrs else 1.0
    tol = annotation.attrs.get("tol")

    #: A digest or graph id is normally quoted truncated in prose, so
    #: `"88496d70b772..."` asks for a prefix match -- which is exactly as much
    #: as a reader of that sentence can verify.
    prefix = stated_text.rstrip(".\u2026")
    elided = prefix != stated_text

    if annotation.is_string:
        produced = clean(resolved.text)
        matched = produced.startswith(prefix) if elided else produced == stated_text
        if not matched:
            return Finding(
                annotation, f"the document disagrees with its artifact: {annotation.label!r}",
                [f"document states : {stated_text!r}",
                 f"artifact states : {produced!r}",
                 f"artifact        : {resolved.detail}"])
    else:
        stated = leading_number(stated_text)
        produced_q = leading_number(resolved.text)
        if stated is None:
            return Finding(annotation, "the annotated value is not a number",
                           [f"value {annotation.value!r}; quote it to compare as text"])
        if produced_q is None:
            return Finding(annotation, f"the artifact holds no number for {annotation.label!r}",
                           [f"artifact states : {resolved.text!r}",
                            f"artifact        : {resolved.detail}"])
        produced = Quantity(produced_q.value * scale, produced_q.quantum * abs(scale) or
                            produced_q.quantum, produced_q.literal)
        ok, allowed = agree(stated, produced, tol)
        if not ok:
            rule = ("tol=" + tol if tol else
                    "half the coarser written precision")
            return Finding(
                annotation, f"the document disagrees with its artifact: {annotation.label!r}",
                [f"document states : {stated.literal}",
                 f"artifact states : {produced.literal}"
                 + (f"  (x{scale:g} = {produced.value:g})" if scale != 1.0 else ""),
                 f"difference      : {abs(stated.value - produced.value):.6g}, "
                 f"allowed {allowed:.6g} ({rule})",
                 f"artifact        : {resolved.detail}",
                 "regenerate the artifact, or correct the document -- do not "
                 "adjust the annotation to agree with a stale number."])

    # The binding check. An annotation that has drifted off the figure it
    # labels is worse than none: it certifies a number nobody compared.
    if annotation.is_string:
        bound = prefix in clean(annotation.scope)
        nearby = "text"
    else:
        stated = leading_number(stated_text)
        candidates = numbers_in(annotation.scope)
        bound = any(agree(stated, candidate, tol)[0] for candidate in candidates)
        nearby = ", ".join(c.literal for c in candidates[:8]) or "(no numbers)"
    if not bound:
        return Finding(
            annotation, f"the annotation no longer labels its figure: {annotation.label!r}",
            [f"annotation says : {stated_text}",
             f"the prose says  : {nearby}",
             f"artifact        : {resolved.detail} = {clean(resolved.text)}",
             "somebody edited the number and not the annotation beside it."])
    return None


def documents(targets: Sequence[Path]) -> list[Path]:
    found: list[Path] = []
    for target in targets:
        path = target if target.is_absolute() else REPO / target
        if path.is_dir():
            found.extend(sorted(p for p in path.rglob("*.md")))
        elif path.is_file():
            found.append(path)
        else:
            raise SystemExit(f"no such document: {target}")
    return found


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check annotated figures in prose against their artifacts.",
        epilog="Tolerance: two numbers agree when they differ by no more than half "
               "the coarser of the two written precisions. 35.3 admits +-0.05.")
    parser.add_argument("targets", nargs="*", type=Path,
                        default=[Path("README.md"), Path("docs")],
                        help="documents or directories (default: README.md and docs/)")
    parser.add_argument("--list", action="store_true",
                        help="print every annotation and the value it resolves to")
    parser.add_argument("--no-coverage", action="store_true",
                        help="skip the per-document annotation floor")
    args = parser.parse_args(argv)

    findings: list[Finding] = []
    per_document: dict[str, int] = {}
    checked = 0
    unbuilt: list[Annotation] = []

    for document in documents(args.targets):
        shown = str(document.resolve().relative_to(REPO)) \
            if document.resolve().is_relative_to(REPO) else str(document)
        try:
            annotations = scan(document)
        except AnnotationError as error:
            print(f"  {shown}: malformed annotation: {error}")
            findings.append(Finding(
                Annotation(document, 0, "", False, {}, "", ""),
                "malformed annotation", [str(error)]))
            continue
        if annotations:
            per_document[shown] = len(annotations)
        for annotation in annotations:
            checked += 1
            if args.list:
                try:
                    resolved = resolve(annotation)
                    print(f"  {annotation.shown}  {annotation.value:>16}  "
                          f"= {clean(resolved.text):<16}  {resolved.detail}")
                except AnnotationError as error:
                    print(f"  {annotation.shown}  {annotation.value:>16}  !! {error}")
            if annotation_needs_a_build(annotation) and not (
                REPO / str(annotation.attrs["src"]).split("#", 1)[0]
            ).exists():
                unbuilt.append(annotation)
            finding = check_annotation(annotation)
            if finding:
                findings.append(finding)

    print(f"provenance-annotated figures: {checked} in {len(per_document)} document(s)")
    for shown, count in sorted(per_document.items()):
        print(f"  {shown}: {count}")

    if not args.no_coverage:
        for shown, floor in sorted(REQUIRED_COVERAGE.items()):
            if (REPO / shown) not in [d.resolve() for d in documents(args.targets)]:
                continue
            have = per_document.get(shown, 0)
            if have < floor:
                findings.append(Finding(
                    Annotation(REPO / shown, 0, "", False, {}, "", ""),
                    f"coverage floor: {have} annotated figures, {floor} required",
                    ["A load-bearing figure lost its provenance. That is exactly how "
                     "80 of 108 figures went stale unnoticed; see docs/EVIDENCE_LEDGER.md."]))

    if findings:
        print(f"\n{len(findings)} problem(s):")
        for finding in findings:
            print(finding.render())
        print("\nSee tools/check_prose_figures.py for the annotation grammar, the "
              "tolerance rule, and the figures nothing produces -- which this "
              "checker cannot see.")
        return 2
    print("\nevery annotated figure still matches the artifact that produces it")
    if unbuilt:
        # Say so rather than let a green line imply full coverage.  A figure
        # bound to a build product is unverifiable by anyone who has not built,
        # which for a published document is a defect even when nothing is wrong
        # with the number.
        print(
            f"\n{len(unbuilt)} figure(s) could NOT be checked here: they cite a "
            "build product that this tree has not built."
        )
        for a in unbuilt:
            print(f"  {a.document.name}:{a.line}  {a.attrs['src']}")
        print(
            "  Build the artifact, or rebind the figure to a tracked artifact "
            "under results/. A published figure should cite evidence a reader "
            "can obtain."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
