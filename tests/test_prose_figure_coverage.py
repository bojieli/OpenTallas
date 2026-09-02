"""The W11.3 census keeps unannotated prose figures visible."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "audit_prose_figure_coverage.py"
SNAPSHOT = ROOT / "results" / "abi3" / "prose_figure_coverage.json"


def _load():
    spec = importlib.util.spec_from_file_location("audit_prose_figure_coverage", TOOL)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


AUDIT = _load()


def _run(*args: str) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(TOOL), *args],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env={"PYTHONPATH": f"{ROOT}:{ROOT / 'src'}", "PATH": "/usr/bin:/bin"},
    )
    return proc.returncode, proc.stdout + proc.stderr


def test_report_covers_and_classifies_the_whole_markdown_corpus() -> None:
    report = AUDIT.build_report(ROOT)
    expected_paths = sorted(
        [
            "README.md",
            *(
                path.relative_to(ROOT).as_posix()
                for path in (ROOT / "docs").rglob("*.md")
            ),
        ]
    )

    assert report["schema"] == "opentallas.prose_figure_coverage.v1"
    assert [document["path"] for document in report["documents"]] == expected_paths
    assert report["totals"]["documents"] == 56
    assert report["totals"]["annotations"] == 805
    assert report["totals"]["zero_candidate_documents"] > 0
    assert report["totals"]["classifications"]["unbound"] > 0

    classifications = set(AUDIT.CLASSIFICATIONS)
    for document in report["documents"]:
        path = ROOT / document["path"]
        assert document["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
        candidates = document["candidates"]
        counts = document["counts"]
        assert counts["candidates"] == len(candidates)
        assert sum(counts["classifications"].values()) == len(candidates)
        assert {
            candidate["classification"] for candidate in candidates
        } <= classifications

    totals = report["totals"]
    assert sum(totals["classifications"].values()) == totals["candidates"]
    assert (
        report["corpus_digest"]
        == hashlib.sha256(AUDIT.canonical_json(report["documents"])).hexdigest()
    )


def test_structural_classification_keeps_exclusions_and_unbound_claims_explicit(
    tmp_path: Path,
) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "empty.md").write_text("# No numeric claims here\n")
    (tmp_path / "README.md").write_text(
        "# Claims\n\n"
        'Power is 5 W. <!-- figure: 5 src="results/example.json#power" -->\n\n'
        "The unsupported estimate is 6 W.\n\n"
        "```text\nA worked example produces 7 W.\n```\n\n"
        "<!-- historical example: 8 W -->\n"
    )

    report = AUDIT.build_report(tmp_path)
    readme = next(item for item in report["documents"] if item["path"] == "README.md")
    candidates = readme["candidates"]

    assert [candidate["classification"] for candidate in candidates] == [
        "provenance_bound",
        "unbound",
        "excluded_context",
        "excluded_context",
    ]
    assert candidates[0]["annotation_lines"] == [3]
    assert candidates[2]["exclusion"] == "fenced_code"
    assert candidates[3]["exclusion"] == "html_comment"
    empty = next(
        item for item in report["documents"] if item["path"] == "docs/empty.md"
    )
    assert empty["counts"]["candidates"] == 0
    assert empty["candidates"] == []


def test_checked_in_snapshot_is_exact_canonical_report() -> None:
    expected = AUDIT.canonical_json(AUDIT.build_report(ROOT))
    assert SNAPSHOT.read_bytes() == expected
    assert json.loads(expected)["totals"]["classifications"]["unbound"] > 0


def test_check_fails_when_a_new_unbound_claim_is_not_snapshotted(
    tmp_path: Path,
) -> None:
    (tmp_path / "docs").mkdir()
    readme = tmp_path / "README.md"
    readme.write_text("# Initially quiet\n")

    code, out = _run("--root", str(tmp_path))
    assert code == 0, out
    code, out = _run("--root", str(tmp_path), "--check")
    assert code == 0, out

    readme.write_text("# Initially quiet\n\nA new unsupported claim is 9.0 W.\n")
    code, out = _run("--root", str(tmp_path), "--check")
    assert code == 1
    assert "coverage drift" in out
