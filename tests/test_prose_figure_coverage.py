"""The W11.3 census and explicit triage keep prose figures visible."""

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

    assert report["schema"] == "opentallas.prose_figure_coverage.v2"
    assert [document["path"] for document in report["documents"]] == expected_paths
    # Derived, not a literal.  This was pinned at 59 while the corpus grew to
    # 70, so the test failed for eleven documents that had been added correctly
    # and were covered correctly.  The load-bearing assertion is the path-list
    # equality above -- that the report covers exactly README plus every
    # docs/*.md -- and this now restates it in a form that cannot go stale.
    assert report["totals"]["documents"] == len(expected_paths)
    assert report["totals"]["annotations"] == 847
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
    assert sum(totals["unbound_triage"].values()) == totals["classifications"][
        "unbound"
    ]
    assert report["triage_policy"]["schema"] == (
        "opentallas.prose_figure_triage_policy.v1"
    )
    assert report["triage_policy"]["rule_count"] > 0
    assert report["triage_policy"]["sha256"]
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
    assert candidates[1]["triage"] == {"disposition": "untriaged"}
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
    triage = json.loads(expected)["totals"]["unbound_triage"]
    assert triage["normative_or_example"] == 8
    assert triage["untriaged"] > 0


def test_explicit_triage_rule_records_disposition_and_provenance(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "README.md").write_text(
        "# Contract example\n\nA shape is `1 x 64`.\n", encoding="utf-8"
    )
    policy = tmp_path / "triage.json"
    policy.write_text(
        json.dumps(
            {
                "schema": "opentallas.prose_figure_triage_policy.v1",
                "rules": [
                    {
                        "id": "shape-separator",
                        "disposition": "normative_or_example",
                        "rationale": "x separates dimensions in this example",
                        "expected_matches": 1,
                        "match": {
                            "path": "README.md",
                            "heading_contains": "Contract example",
                            "literal": "1 x",
                            "line_contains": "shape",
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    report = AUDIT.build_report(tmp_path, policy)
    readme = next(item for item in report["documents"] if item["path"] == "README.md")
    candidate = readme["candidates"][0]
    assert candidate["heading_path"] == ["Contract example"]
    assert candidate["triage"] == {
        "disposition": "normative_or_example",
        "rule": "shape-separator",
        "rationale": "x separates dimensions in this example",
    }
    assert report["totals"]["unbound_triage"]["normative_or_example"] == 1
    assert report["totals"]["unbound_triage"]["untriaged"] == 0


def test_triage_policy_fails_closed_on_stale_or_ambiguous_rules(
    tmp_path: Path,
) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "README.md").write_text("# Claim\n\nPower is 5 W.\n", encoding="utf-8")
    policy = tmp_path / "triage.json"

    stale_rule = {
        "id": "stale",
        "disposition": "missing_producer",
        "rationale": "no machine producer exists",
        "expected_matches": 1,
        "match": {"path": "README.md", "literal": "6 W"},
    }
    policy.write_text(
        json.dumps(
            {
                "schema": "opentallas.prose_figure_triage_policy.v1",
                "rules": [stale_rule],
            }
        ),
        encoding="utf-8",
    )
    try:
        AUDIT.build_report(tmp_path, policy)
    except ValueError as exc:
        assert "matched 0 candidates; expected 1" in str(exc)
    else:
        raise AssertionError("stale triage selector was accepted")

    broad = {
        **stale_rule,
        "id": "broad-a",
        "match": {"path": "README.md", "literal": "5 W"},
    }
    duplicate = {**broad, "id": "broad-b"}
    policy.write_text(
        json.dumps(
            {
                "schema": "opentallas.prose_figure_triage_policy.v1",
                "rules": [broad, duplicate],
            }
        ),
        encoding="utf-8",
    )
    try:
        AUDIT.build_report(tmp_path, policy)
    except ValueError as exc:
        assert "ambiguous prose triage" in str(exc)
    else:
        raise AssertionError("ambiguous triage selectors were accepted")


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
