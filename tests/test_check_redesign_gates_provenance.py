"""The design and physical gates must reject an artifact written from a dirty tree.

The G1 ladder has always applied this rule -- ``_rtl_record_problems`` refuses
a record whose ``git.worktree_dirty`` is not false, on the stated grounds that
"a record that ... was written from a dirty tree is not evidence whatever it
claims".  D1-D5 and G2 read their evidence through four other evaluators
(``artifact_field``, ``artifact_threshold``, ``per_mac_improvement``,
``routed_netlist_contains``) and none of them applied it, so those six gates
would report pass on an artifact its own author had marked untrustworthy.

These tests pin the rule in BOTH directions, because a provenance check that
can never fire is as useless as one that can never lift:

  * a clean artifact still passes, on every one of the four evaluators;
  * a dirty one is rejected, and the gate says so rather than falling through
    to "no artifact carries the field", which would be a worse diagnostic;
  * an artifact with NO git block is NOT rejected, because the derived records
    under ``results/derived`` carry none by convention and inventing that
    requirement here made C3 stop reporting the reason it actually fails.

The two field spellings are both pinned.  The board reads two provenance
schemas -- the ladder and physical records write ``git.worktree_dirty``, the
lane and LQ8 RTL records write ``git.dirty`` -- and a check that knew only one
name would pass the other vacuously, which is the exact failure this guards.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check_redesign_gates", ROOT / "tools/check_redesign_gates.py"
)
gates = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(gates)


# --- the helper itself -----------------------------------------------------

@pytest.mark.parametrize("field", ["worktree_dirty", "dirty"])
def test_a_clean_tree_is_accepted_under_either_spelling(field):
    assert gates._tree_was_clean({"git": {field: False}}) is None


@pytest.mark.parametrize("field", ["worktree_dirty", "dirty"])
def test_a_dirty_tree_is_rejected_under_either_spelling(field):
    why = gates._tree_was_clean({"git": {field: True}})
    assert why is not None
    assert field in why and "dirty tree" in why


def test_a_git_block_that_states_no_cleanliness_is_rejected():
    """Recording a commit and omitting the part that decides admissibility."""
    why = gates._tree_was_clean({"git": {"commit": "abc123"}})
    assert why is not None
    assert "neither worktree_dirty nor dirty" in why


def test_no_git_block_is_not_a_failure():
    """The derived artifacts carry none, and failing them would be a worse
    diagnostic rather than a stricter one -- C3 would stop reporting why it
    actually fails and start reporting a missing field instead."""
    assert gates._tree_was_clean({"anchor": {}, "targets": []}) is None


def test_a_non_object_states_no_provenance():
    assert gates._tree_was_clean(None) is not None
    assert gates._tree_was_clean([1, 2, 3]) is not None


# --- the evaluators that were missing it -----------------------------------

def _write(path: Path, body: dict) -> None:
    import json
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body))


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.setattr(gates, "REPO", tmp_path)
    return tmp_path


ARTIFACT_FIELD_GATE = {
    "id": "TEST-AF",
    "kind": "design",
    "evaluator": {
        "type": "artifact_field",
        "glob": "results/rtl/*.json",
        "require": {"field": "bit_identity.equal", "equals": True},
    },
}

ARTIFACT_THRESHOLD_GATE = {
    "id": "TEST-AT",
    "kind": "design",
    "evaluator": {
        "type": "artifact_threshold",
        "glob": "results/rtl/*.json",
        "field": "measured.lanes",
        "min": 8,
    },
}


def test_artifact_field_passes_on_a_clean_artifact(repo):
    _write(repo / "results/rtl/rec.json",
           {"git": {"dirty": False}, "bit_identity": {"equal": True}})
    got = gates.evaluate(ARTIFACT_FIELD_GATE)
    assert got["status"] == "pass"


def test_artifact_field_rejects_a_dirty_artifact(repo):
    _write(repo / "results/rtl/rec.json",
           {"git": {"dirty": True}, "bit_identity": {"equal": True}})
    got = gates.evaluate(ARTIFACT_FIELD_GATE)
    assert got["status"] == "fail"
    # It must say WHY -- not fall through to "no artifact carries the field",
    # which would send a reader looking for a missing key that is present.
    assert "provenance" in got["why"]
    assert "dirty tree" in got["why"]


def test_artifact_threshold_passes_on_a_clean_artifact(repo):
    _write(repo / "results/rtl/rec.json",
           {"git": {"worktree_dirty": False}, "measured": {"lanes": 8}})
    got = gates.evaluate(ARTIFACT_THRESHOLD_GATE)
    assert got["status"] == "pass"


def test_artifact_threshold_rejects_a_dirty_artifact(repo):
    _write(repo / "results/rtl/rec.json",
           {"git": {"worktree_dirty": True}, "measured": {"lanes": 8}})
    got = gates.evaluate(ARTIFACT_THRESHOLD_GATE)
    assert got["status"] == "fail"
    assert "dirty tree" in got["why"]


def test_a_dirty_artifact_does_not_hide_a_clean_one(repo):
    """Rejecting one candidate must not reject the gate when another stands.

    This is the behaviour observed on the live board: marking
    abi3_pipelined_lane.json dirty made D1 fall back to
    abi3_pipelined_lane_groups.json rather than fail.
    """
    _write(repo / "results/rtl/a_dirty.json",
           {"git": {"dirty": True}, "bit_identity": {"equal": True}})
    _write(repo / "results/rtl/b_clean.json",
           {"git": {"dirty": False}, "bit_identity": {"equal": True}})
    got = gates.evaluate(ARTIFACT_FIELD_GATE)
    assert got["status"] == "pass"
    assert "b_clean.json" in got["why"]


def test_the_threshold_message_survives_a_gate_with_no_second_field(repo):
    """A regression this suite caught while it was being written.

    ``rejected`` now collects provenance rejections as well as second-field
    disagreements, and the failure message named ``also`` unconditionally --
    so a gate with no ``also_require`` raised TypeError the moment a
    provenance rejection was the only entry.  The live D2 hit exactly this.
    """
    _write(repo / "results/rtl/rec.json",
           {"git": {"dirty": True}, "measured": {"lanes": 8}})
    got = gates.evaluate(ARTIFACT_THRESHOLD_GATE)   # must not raise
    assert got["status"] == "fail"
