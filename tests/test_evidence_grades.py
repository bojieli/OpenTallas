"""The grade vocabulary must be enforceable, and the enforcement must bite.

Three numbers were wrong in one night and they failed the same way: each carried
an evidence grade stronger than its evidence. The grading scheme was not the
problem -- all 151 entries already cited a source. What was missing was anything
that checked a grade against what it asserts.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/check_evidence_grades.py"
TECHNOLOGY = ROOT / "configs/hardware/technology.json"


def _run(technology: Path) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(TOOL), "--technology", str(technology)],
        capture_output=True, text=True, cwd=ROOT,
        env={"PYTHONPATH": f"{ROOT}:{ROOT / 'src'}", "PATH": "/usr/bin:/bin"},
    )
    return proc.returncode, proc.stdout


def test_the_checked_in_technology_passes() -> None:
    code, out = _run(TECHNOLOGY)
    assert code == 0, out


def test_an_undefined_grade_is_refused(tmp_path) -> None:
    """The exact defect: `measured_bracket` was invented and nothing objected."""

    body = json.loads(TECHNOLOGY.read_text())
    body["rom"]["cross_checks"][0]["grade"] = "measured_bracket"
    broken = tmp_path / "technology.json"
    broken.write_text(json.dumps(body))

    code, out = _run(broken)
    assert code == 2
    assert "measured_bracket" in out and "not defined" in out


def test_a_publication_claim_needs_a_findable_document(tmp_path) -> None:
    body = json.loads(TECHNOLOGY.read_text())
    body["energy"]["hbm_j_per_byte"]["source"] = "everyone knows this"
    broken = tmp_path / "technology.json"
    broken.write_text(json.dumps(body))

    code, out = _run(broken)
    assert code == 2
    assert "no link, no DOI, no year" in out


def test_an_executed_claim_needs_an_artifact_that_exists(tmp_path) -> None:
    """`executed` says we ran it. A citation to a file that is not there is not
    evidence, however true it was when written -- which is how a correction came
    to cite oracle rungs that had been rebuilt away."""

    body = json.loads(TECHNOLOGY.read_text())
    body["rom"]["cross_checks"][0] = {
        "grade": "executed",
        "name": "invented",
        "value": 1.0,
        "source": "a run that happened",
        "artifact": "results/roofline/this_was_never_committed.json",
    }
    broken = tmp_path / "technology.json"
    broken.write_text(json.dumps(body))

    code, out = _run(broken)
    assert code == 2
    assert "not in the repository" in out


def test_the_vocabulary_distinguishes_our_runs_from_published_silicon() -> None:
    """`measured` and `executed` must not be conflated.

    `measured` means fabricated silicon in a peer-reviewed venue and needs a
    citation; `executed` means we ran it and needs a committed artifact. Asking a
    journal paper for a repository path, or our own run for a DOI, are both
    category errors -- and the checker made the first one on its first draft.
    """

    definitions = json.loads(TECHNOLOGY.read_text())["grade_definitions"]
    assert {"measured", "executed", "published", "derived", "assumed"} <= set(definitions)
    assert "peer-reviewed" in definitions["measured"]
    assert "this repository" in definitions["executed"]
