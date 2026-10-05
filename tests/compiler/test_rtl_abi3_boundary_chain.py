"""The dependent-boundary chain record must stay a refusal, not a number.

``results/rtl/abi3_boundary_chain.json`` exists to make G4's boundary
failure specific.  The one thing it must never become is a boundary
measurement by accident: ``tools/derive_cycle_machine.py`` reads
``boundary.is_the_section_13_item_13_boundary`` and would treat a record that
stopped declaring itself a probe as the measurement section 13 item 13 asks
for.  These tests pin that, and pin that the structural verdicts came from
both elaborators rather than from anyone's reading of the source.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "results/rtl/abi3_boundary_chain.json"


@pytest.fixture(scope="module")
def artifact() -> dict:
    if not ARTIFACT.exists():
        pytest.skip(f"{ARTIFACT} has not been produced")
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def test_it_declares_itself_not_the_boundary(artifact: dict) -> None:
    boundary = artifact["boundary"]
    assert boundary["is_the_section_13_item_13_boundary"] is False
    assert boundary["cycles"] is None
    assert boundary["simulators_agree"] is False
    assert boundary["per_simulator"] == []
    assert boundary["why_not"].strip()


def test_the_calibration_reads_it_as_unmeasured(artifact: dict) -> None:
    """The consumer's own reader, not a restatement of what it should say."""
    import sys

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from tools.derive_cycle_machine import _boundary_measurement

    verdict = _boundary_measurement(artifact)
    assert verdict["measured"] is False
    assert verdict["rtl_measured_boundary_cycles"] is None
    assert artifact["boundary"]["why_not"] in verdict["why"]


def test_every_verdict_came_from_both_elaborators(artifact: dict) -> None:
    rows = artifact["measured"]["signals"]
    assert rows, "a probe with no signals establishes nothing"
    for row in rows:
        simulators = sorted(r["simulator"] for r in row["per_simulator"])
        assert simulators == ["iverilog", "verilator"], row["signal"]
        assert row["simulators_agree"] is True, row["signal"]
        assert row["as_expected"] is True, row["signal"]
        # A refusal has to quote the tool that refused; a port has none.
        for result in row["per_simulator"]:
            if result["is_a_port"]:
                assert result["diagnostic"] is None
            else:
                assert row["signal"] in str(result["diagnostic"])


def test_the_chain_is_still_missing_both_of_its_blocks(artifact: dict) -> None:
    """If either block is ever built, this test is how the record finds out."""
    terms = {t["term"]: t for t in artifact["terms"]}
    assert terms["the collector between them"]["exists"] is False
    assert terms["operand readiness and queue admission"]["exists"] is False
    # And the blocks that do exist say which campaign qualified them.
    for name in (
        "the last result",
        "the reduction over the producer's partials",
        "mesh transfer",
        "acknowledged completion",
    ):
        assert terms[name]["exists"] is True
        assert terms[name]["qualified_by"]


def test_it_charges_nothing_into_the_technology_file(artifact: dict) -> None:
    """No figure for the missing blocks, and no edit to what prices them."""
    assert "any_figure_for_the_missing_blocks" in artifact["does_not_establish"]
    technology = json.loads(
        (ROOT / "configs/hardware/technology.json").read_text(encoding="utf-8")
    )
    assert technology["latency"]["pipeline_fill_drain_s"]["grade"] == "assumed"


def test_the_record_is_source_bound_and_clean(artifact: dict) -> None:
    assert artifact["git"]["worktree_dirty"] is False
    assert len(artifact["git"]["commit"]) == 40
    for path, digest in artifact["source_sha256"].items():
        assert (ROOT / path).exists(), path
        assert len(digest) == 64
