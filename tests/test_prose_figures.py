"""A checker nobody can fail is decoration, so this file tries to fail it.

`docs/EVIDENCE_LEDGER.md` audited ~1,100 numeric tokens and found 80 of 108
load-bearing figures stale. Its finding was structural: the documents that cite
artifacts had their errors caught and retracted, and the ones that cite nothing
still carry them live. `tools/check_prose_figures.py` is the answer to that --
it reads a provenance annotation beside a figure, resolves it against the
artifact, and refuses a disagreement.

Two things have to be true for it to be worth having, and both are tested here:

  1. It PASSES on the committed tree. Those documents were corrected, so a
     failure here means either a document went stale or an artifact was
     regenerated without one.
  2. It FAILS on a mutation, naming the document, the figure and the artifact's
     value -- in both directions. Editing the prose and leaving the annotation
     is caught; editing both to agree with each other is caught by the artifact.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/check_prose_figures.py"

#: The figure this file mutates, and the artifact that produces it. Chosen
#: because it is the exact number the 2026-08-30 correction moved: the
#: weight-to-KV ratio fell from a retracted 113.2 to 35.3358.
TRAFFIC_DOC = ROOT / "docs/OVERVIEW.md"
STATED = "**35.3358×**"
ARTIFACT_VALUE = "35.33578981"


def _load():
    spec = importlib.util.spec_from_file_location("check_prose_figures", TOOL)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


CPF = _load()


def _run(*targets: Path | str) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(TOOL), *(str(t) for t in targets)],
        capture_output=True, text=True, cwd=ROOT,
        env={"PYTHONPATH": f"{ROOT}:{ROOT / 'src'}", "PATH": "/usr/bin:/bin"},
    )
    return proc.returncode, proc.stdout + proc.stderr


def _copy(tmp_path: Path, source: Path, *replacements: tuple[str, str]) -> Path:
    body = source.read_text()
    for old, new in replacements:
        assert old in body, f"anchor {old!r} is no longer in {source.name}"
        body = body.replace(old, new, 1)
    target = tmp_path / source.name
    target.write_text(body)
    return target


# --------------------------------------------------------------------------
# 1. it passes on what is committed


def test_the_committed_tree_passes() -> None:
    """The documents were corrected; the artifacts were regenerated. If this
    fails, one of the two moved and the other did not -- which is the entire
    defect this checker exists to catch."""

    code, out = _run()
    assert code == 0, out
    assert "every annotated figure still matches" in out


def test_every_annotated_release_document_carries_pinned_provenance() -> None:
    """Every document publishing checked figures has a non-regressing floor.

    The original audit pinned only the worst-affected files. That still allowed
    all annotations to disappear from a later evidence document without making
    the aggregate checker fail. Coverage is the finding, so all current
    annotated release documents are pinned.
    """

    code, out = _run()
    assert code == 0, out
    annotated_documents = {
        str(document.resolve().relative_to(ROOT)): len(CPF.scan(document))
        for document in CPF.documents([Path("README.md"), Path("docs")])
        if CPF.scan(document)
    }
    assert annotated_documents == CPF.REQUIRED_COVERAGE
    # 936, not 930: WP-P of the DeepSeek-V4.1 plan registered the three new
    # targets in docs/FOUR_TARGET_IMPLEMENTATION_MASTER_PLAN.md section 3 and
    # docs/TENSOR_ACCELERATOR_ABI_3_ARCHITECTURE_DECISION.md section 3.3, which
    # enter this map at 2 annotations each, and added two area figures to
    # docs/EVIDENCE_LEDGER.md section 10 (42 -> 44).  Before that
    # docs/DEEPSEEK_V41_FLASH_ROM_IMPLEMENTATION_PLAN.md was added with 14
    # annotations, after ANALYTICAL_REPORT.md's 69 (and before that
    # docs/CHIP_ARCHITECTURE_DESIGN.md gained ten and its floor was raised to
    # match).  This total only ever moves UP -- a drop is the regression the
    # floor exists to catch, and the per-document equality above catches it
    # first.
    # 700, down from 936, and deliberately: on 2026-09-23 the legacy analytical
    # reports were deleted at the user's direction and replaced by
    # docs/ANALYTICAL_REPORT.md (77 annotations). The iso-node headline
    # sections of README.md and docs/OVERVIEW.md went with them. This is the one
    # sanctioned drop; the floor rises again from here.
    assert sum(CPF.REQUIRED_COVERAGE.values()) == 700
    for document in CPF.REQUIRED_COVERAGE:
        assert document in out, f"{document} reports no annotated figures"


# --------------------------------------------------------------------------
# 2. the mutation


def test_a_mutated_figure_is_rejected(tmp_path) -> None:
    """The mutation that matters: someone edits the number and not the
    annotation. The rejection has to name the document, the figure and the
    artifact's value, or a reader cannot act on it."""

    broken = _copy(tmp_path, TRAFFIC_DOC, (STATED, "**36.1×**"))
    code, out = _run(broken)

    assert code == 2
    assert "no longer labels its figure" in out
    assert broken.name in out                      # the document
    assert "Flash W:KV at 200K, B=1" in out        # the figure
    assert "35.3358" in out and "36.1" in out      # annotated vs prose
    assert ARTIFACT_VALUE in out                   # the artifact's value
    assert "results/model-traffic/sweep.csv" in out


def test_a_mutation_that_updates_the_annotation_too_is_still_rejected(tmp_path) -> None:
    """The determined version of the same mistake: edit the figure AND the
    annotation so they agree with each other. Only the artifact can settle it,
    and the artifact is what the checker reads."""

    broken = _copy(tmp_path, TRAFFIC_DOC,
                   (STATED, "**36.1×**"),
                   ("figure: 35.3358 ", "figure: 36.1 "))
    code, out = _run(broken)

    assert code == 2
    assert "disagrees with its artifact" in out
    assert broken.name in out
    assert "Flash W:KV at 200K, B=1" in out
    assert "document states : 36.1" in out
    assert ARTIFACT_VALUE in out
    assert "do not adjust the annotation to agree with a stale number" in out


def test_a_stale_digest_is_rejected(tmp_path) -> None:
    """A graph id is quoted truncated in prose, so it is checked as a prefix.
    `docs/PROGRAM_STATUS.md` shipped a stale one for 100+ commits."""

    checklist = ROOT / "docs" / "UNIFIED_EXECUTION_CHECKLIST.md"
    broken = _copy(tmp_path, checklist,
                   ("`84bb97dd1243…`", "`65eb209fdead…`"),
                   ('figure: "84bb97dd1243…"', 'figure: "65eb209fdead…"'))
    code, out = _run(broken)

    assert code == 2
    assert "Qwen graph id" in out
    assert "65eb209fdead" in out and "84bb97dd1243" in out


# --------------------------------------------------------------------------
# 3. tolerant of formatting, strict about value


@pytest.mark.parametrize("stated", ["35.3", "35.30", "35.3:1", "**35.3**", "`35.3`",
                                   "35.3 GB", "35.3×", "35.3x"])
def test_formatting_is_not_value(stated: str) -> None:
    """`35.3:1`, `35.3` and `35.30` are the same number, however they are dressed."""

    assert CPF.agree(CPF.leading_number(stated), CPF.leading_number("35.3"), None)[0]


@pytest.mark.parametrize("stated", ["35.3", "35.3:1", "35.34", "35.336", "35.3358"])
def test_a_correct_rounding_of_the_artifact_agrees(stated: str) -> None:
    """Every one of these is what a careful author writes for 35.33578981."""

    produced = CPF.leading_number("35.33578981357011")
    assert CPF.agree(CPF.leading_number(stated), produced, None)[0], stated


@pytest.mark.parametrize("stated", ["36.1", "35.4", "35.33", "113.2", "3.53", "353"])
def test_a_different_number_does_not_agree(stated: str) -> None:
    produced = CPF.leading_number("35.33578981357011")
    assert not CPF.agree(CPF.leading_number(stated), produced, None)[0], stated


def test_the_tolerance_is_half_the_coarser_written_precision() -> None:
    """The rule the docstring states must be the rule that runs, because it is
    the only thing standing between "tolerant of formatting" and "tolerant"."""

    assert "half of the coarser of\n    the two written precisions" in CPF.__doc__
    _, allowed = CPF.agree(CPF.leading_number("35.3"),
                           CPF.leading_number("35.33578981"), None)
    assert allowed == pytest.approx(0.05)
    # An artifact rounded in its own table is met at its own precision.
    _, allowed = CPF.agree(CPF.leading_number("8.63"), CPF.leading_number("8.6x"), None)
    assert allowed == pytest.approx(0.05)
    # A four-figure quote is held to four figures.
    _, allowed = CPF.agree(CPF.leading_number("35.3358"),
                           CPF.leading_number("35.33578981"), None)
    assert allowed == pytest.approx(0.00005)


def test_an_explicit_tolerance_only_ever_loosens() -> None:
    stated, produced = CPF.leading_number("9,000"), CPF.leading_number("9,018.8")
    assert not CPF.agree(stated, produced, None)[0]
    assert CPF.agree(stated, produced, "1%")[0]
    # It cannot tighten below the written precision...
    assert CPF.agree(CPF.leading_number("35.3"),
                     CPF.leading_number("35.33578981"), "0.0001")[0]
    # ...except where the author asks for equality outright.
    assert not CPF.agree(CPF.leading_number("35.3"),
                         CPF.leading_number("35.33578981"), "exact")[0]


# --------------------------------------------------------------------------
# 4. silent on prose it was not asked about


def test_it_says_nothing_about_unannotated_prose(tmp_path) -> None:
    """A checker that flags every year and version string is one nobody runs."""

    quiet = tmp_path / "quiet.md"
    quiet.write_text(
        "# A document with no annotations\n\n"
        "In 2026 the v3.1 release moved the ratio from 54.2x to 8.6x across\n"
        "six corrections, at 16,960 tok/s and 46,225 mm2.\n")
    code, out = _run(quiet)
    assert code == 0
    assert "0 in 0 document(s)" in out


def test_an_annotation_inside_a_code_fence_is_an_example_not_a_claim(tmp_path) -> None:
    fenced = tmp_path / "fenced.md"
    fenced.write_text(
        "# Docs\n\n```\n"
        '<!-- figure: 1.0 src="results/nowhere.json#a.b" -->\n'
        "```\n")
    code, out = _run(fenced)
    assert code == 0, out
    assert "0 in 0 document(s)" in out


# --------------------------------------------------------------------------
# 5. the annotation must be resolvable without guessing


def test_a_line_number_is_not_a_selector() -> None:
    """The audit found the ledger's own `FILE.md:52` references had drifted
    while the values they pointed at still held. No annotation may address an
    artifact by line."""

    import re
    offenders = []
    for document in sorted(ROOT.joinpath("docs").rglob("*.md")) + [ROOT / "README.md"]:
        for annotation in CPF.scan(document):
            if re.search(r"#L?\d+\b", annotation.attrs.get("src", "")):
                offenders.append(f"{annotation.shown} {annotation.attrs['src']}")
    assert not offenders, offenders


@pytest.mark.parametrize("body, expected", [
    ('1.0 src="results/nowhere.json#a.b"', "not in the repository"),
    ('1.0 src="results/model-traffic/sweep.csv"', "names a file but no field"),
    ('1.0 src="results/abi3/program_status.json#neutral_ir.nope"', "does not exist"),
    ('1.0 src="results/model-traffic/sweep.csv#no_such_column" where="model=x"',
     "has no column"),
    ('1.0 src="results/roofline/n6_vs_a100/REPORT.md#Ratio after" where="Model=Qwen3-8B"',
     'add table="..." to disambiguate'),
    ('1.0 srcc="results/x.json#a"', "unknown attribute"),
    ('1.0', "no src="),
])
def test_an_unresolvable_annotation_is_refused(tmp_path, body: str, expected: str) -> None:
    """A typo must not quietly disable a check, and an ambiguous row selector
    must not silently pick the first match."""

    document = tmp_path / "bad.md"
    document.write_text(f"# x\n\n<!-- figure: {body} -->\nThe value is 1.0.\n")
    code, out = _run(document)
    assert code == 2, out
    assert expected in out


def test_an_ambiguous_row_is_disambiguated_by_its_table(tmp_path) -> None:
    # The value is read from a live generated report, so it moves when
    # `make roofline` reruns and this literal has to move with it -- which is
    # the same discipline the checker imposes on prose. It was 9.50 before the
    # per-model design rule, 8.98 after it, 5.76 after the scale-out link
    # evidence was corrected, and 6.16 after the 2026-09-23 framework revision.
    document = tmp_path / "ok.md"
    document.write_text(
        "# x\n\n"
        '<!-- figure: 6.16 src="results/roofline/n6_vs_a100/REPORT.md#Ratio after"'
        ' table="latency separation" where="Model=DeepSeek-V4-Flash-0731;mm2=554700" -->\n'
        "The ratio is 6.16x.\n")
    code, out = _run(document)
    assert code == 0, out


# --------------------------------------------------------------------------
# 6. coverage cannot be deleted quietly


def test_removing_the_annotations_from_a_priority_document_fails(tmp_path, capsys,
                                                                monkeypatch) -> None:
    """Provenance is what separated the caught errors from the live ones, so
    losing it on a priority document is itself the regression."""

    monkeypatch.setattr(CPF, "REQUIRED_COVERAGE", {"docs/ANALYTICAL_REPORT.md": 60})
    assert CPF.main(["docs/ANALYTICAL_REPORT.md"]) == 0

    monkeypatch.setattr(CPF, "REQUIRED_COVERAGE", {"docs/ANALYTICAL_REPORT.md": 500})
    assert CPF.main(["docs/ANALYTICAL_REPORT.md"]) == 2
    assert "coverage floor" in capsys.readouterr().out


# --------------------------------------------------------------------------
# 7. the blind spot must stay named


def test_the_figures_nothing_produces_are_named_in_the_docstring() -> None:
    """The most durable part of the audit was the list of figures no script,
    artifact or test emits. They cannot be annotated, this checker cannot see
    them, and deleting the list would make the gap invisible again."""

    doc = CPF.__doc__
    assert "ITS STATED BLIND SPOT" in doc
    for figure in ["16,960 tok/s", "46,225 mm2", "823 mm2", "84.7%", "290.4 ns",
                   "11,747 feasible points", "100.4 mm2", "1.4 us"]:
        assert figure in doc, figure
    assert "Do not invent a producer for one of these" in doc
