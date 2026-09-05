"""Gate G1 must not pass on a file name.

G1 says the integrated RTL produces the oracle's token IDs for one governed
workload, on each of ROM and HBM.  Its first evaluator was ``artifact_field``
over ``results/rtl/*token*.json`` requiring only ``record.oracle.agreement ==
true``: it checked neither storage class, nor the workload, nor that any RTL
ran, so any file matching that glob would have turned a terminal gate green.
That is the ``not_evaluable`` defect the redesign plan exists to remove, and
it is the third instance on this same board -- G2 passed on a directory NAME,
G4 on half its statement.

These tests pin both directions.  A gate that cannot fail is a note; a gate
that cannot pass is worse, because it hides the work.  So they pin the
refusals AND the one shape that is accepted.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check_redesign_gates", ROOT / "tools/check_redesign_gates.py"
)
gates = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(gates)

ORACLE_REL = "results/abi3/qwen3_reference_oracle_eos.json"
GOLD = [3925, 13, 151645]

G1 = {
    "type": "token_record",
    "glob": "results/rtl/*token*.json",
    "require_storage_classes": ["rom", "hbm"],
    "workload": "TA-QW-EOS-1",
    "oracle": ORACLE_REL,
    "oracle_token_field": "generated_token_ids",
}


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.setattr(gates, "REPO", tmp_path)
    oracle = tmp_path / ORACLE_REL
    oracle.parent.mkdir(parents=True, exist_ok=True)
    oracle.write_text(json.dumps({"generated_token_ids": GOLD}))
    return tmp_path


def _digest(repo: Path) -> str:
    return hashlib.sha256((repo / ORACLE_REL).read_bytes()).hexdigest()


def _record(repo: Path, storage_class: str, **over) -> dict:
    body = {
        "storage_class": storage_class,
        "workload_id": "TA-QW-EOS-1",
        "record_token_ids": list(GOLD),
        "oracle": {
            "artifact": ORACLE_REL,
            "artifact_sha256": _digest(repo),
            "generated_token_ids": list(GOLD),
            "agreement": True,
        },
        "execution": {
            "simulator": "verilator-5.050",
            "simulated_cycles": 22_719_332_352,
            "evidence_class": "public_open_tool_rtl_simulation",
        },
        "git": {"commit": "0" * 40, "worktree_dirty": False},
    }
    for key, value in over.items():
        if value is None:
            body.pop(key, None)
        elif isinstance(value, dict) and isinstance(body.get(key), dict):
            merged = dict(body[key])
            for k, v in value.items():
                if v is None:
                    merged.pop(k, None)
                else:
                    merged[k] = v
            body[key] = merged
        else:
            body[key] = value
    return body


def _write(repo: Path, rel: str, body: dict) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body))


def _evaluate() -> dict:
    return gates.evaluate({"id": "G1", "evaluator": G1})


def test_no_artifact_at_all_fails(repo):
    assert _evaluate()["status"] == "fail"


def test_the_old_evaluators_pass_shape_is_refused(repo):
    """A bare {"record": {"oracle": {"agreement": true}}} used to pass G1."""
    _write(repo, "results/rtl/abi3_token.json", {"record": {"oracle": {"agreement": True}}})
    got = _evaluate()
    assert got["status"] == "fail"
    assert "storage_class" in got["why"]


def test_one_storage_class_alone_fails_and_names_the_missing_one(repo):
    _write(repo, "results/rtl/abi3_token_rom.json", _record(repo, "rom"))
    got = _evaluate()
    assert got["status"] == "fail"
    assert "hbm" in got["why"]


def test_wrong_workload_fails(repo):
    _write(repo, "results/rtl/abi3_token_rom.json", _record(repo, "rom", workload_id="TA-QW-CHAT-1"))
    _write(repo, "results/rtl/abi3_token_hbm.json", _record(repo, "hbm"))
    got = _evaluate()
    assert got["status"] == "fail"
    assert "workload_id" in got["why"]


def test_token_ids_that_differ_from_the_oracle_fail(repo):
    _write(repo, "results/rtl/abi3_token_rom.json", _record(repo, "rom", record_token_ids=[3925, 13, 13]))
    _write(repo, "results/rtl/abi3_token_hbm.json", _record(repo, "hbm"))
    got = _evaluate()
    assert got["status"] == "fail"
    assert "token ids" in got["why"]


def test_a_record_that_states_no_emitted_ids_fails(repo):
    """Agreement claimed with nothing of the RTL's own to compare."""
    _write(repo, "results/rtl/abi3_token_rom.json", _record(repo, "rom", record_token_ids=None))
    _write(repo, "results/rtl/abi3_token_hbm.json", _record(repo, "hbm"))
    got = _evaluate()
    assert got["status"] == "fail"
    assert "record_token_ids absent" in got["why"]


def test_an_oracle_digest_that_does_not_match_the_file_fails(repo):
    _write(repo, "results/rtl/abi3_token_rom.json", _record(repo, "rom", oracle={"artifact_sha256": "f" * 64}))
    _write(repo, "results/rtl/abi3_token_hbm.json", _record(repo, "hbm"))
    got = _evaluate()
    assert got["status"] == "fail"
    assert "oracle.artifact_sha256" in got["why"]


def test_a_record_naming_no_simulator_fails(repo):
    _write(repo, "results/rtl/abi3_token_rom.json", _record(repo, "rom", execution={"simulator": None}))
    _write(repo, "results/rtl/abi3_token_hbm.json", _record(repo, "hbm"))
    got = _evaluate()
    assert got["status"] == "fail"
    assert "execution.simulator absent" in got["why"]


def test_zero_simulated_cycles_fails(repo):
    _write(repo, "results/rtl/abi3_token_rom.json", _record(repo, "rom", execution={"simulated_cycles": 0}))
    _write(repo, "results/rtl/abi3_token_hbm.json", _record(repo, "hbm"))
    got = _evaluate()
    assert got["status"] == "fail"
    assert "simulated_cycles" in got["why"]


def test_a_functional_simulator_record_does_not_satisfy_an_RTL_gate(repo):
    """The functional path already agrees with the oracle on both stores."""
    _write(
        repo,
        "results/rtl/abi3_token_rom.json",
        _record(repo, "rom", execution={"evidence_class": "functional_artifact_only"}),
    )
    _write(repo, "results/rtl/abi3_token_hbm.json", _record(repo, "hbm"))
    got = _evaluate()
    assert got["status"] == "fail"
    assert "evidence_class" in got["why"]


def test_a_dirty_worktree_fails(repo):
    _write(repo, "results/rtl/abi3_token_rom.json", _record(repo, "rom", git={"worktree_dirty": True}))
    _write(repo, "results/rtl/abi3_token_hbm.json", _record(repo, "hbm"))
    got = _evaluate()
    assert got["status"] == "fail"
    assert "worktree_dirty" in got["why"]


def test_both_stores_conforming_passes(repo):
    _write(repo, "results/rtl/abi3_token_rom.json", _record(repo, "rom"))
    _write(repo, "results/rtl/abi3_token_hbm.json", _record(repo, "hbm"))
    got = _evaluate()
    assert got["status"] == "pass", got["why"]
    assert "rom" in got["why"] and "hbm" in got["why"]


def test_both_stores_in_one_artifact_passes(repo):
    _write(
        repo,
        "results/rtl/abi3_g1_token.json",
        {"records": [_record(repo, "rom"), _record(repo, "hbm")]},
    )
    assert _evaluate()["status"] == "pass"


def test_a_missing_oracle_file_fails_rather_than_passing_vacuously(repo):
    rom = _record(repo, "rom")
    hbm = _record(repo, "hbm")
    (repo / ORACLE_REL).unlink()
    _write(repo, "results/rtl/abi3_token_rom.json", rom)
    _write(repo, "results/rtl/abi3_token_hbm.json", hbm)
    got = _evaluate()
    assert got["status"] == "fail"
    assert "oracle artifact" in got["why"]
