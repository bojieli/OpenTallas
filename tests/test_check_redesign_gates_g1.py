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


# ---------------------------------------------------------------------------
# The roll-up.  G1 is a verification pyramid, not a run: it passes only when
# every rung passes AND a mechanically derived certificate binds them.  These
# pin that a roll-up can never be greener than the evidence under it.
# ---------------------------------------------------------------------------

CERT_REL = "results/rtl/abi3_g1_composition_certificate.json"

ROLLUP = {
    "type": "gate_rollup",
    "requires": ["G1a", "G1b"],
    "certificate": CERT_REL,
    "certificate_requires": [
        {"field": "certificate.every_issued_instance_covered", "equals": True},
        {"field": "certificate.uncovered_instance_count", "equals": 0},
    ],
}


def _rung(gid: str, artifact: str, field: str) -> dict:
    return {
        "id": gid,
        "kind": "verification",
        "statement": gid,
        "fails_when": "-",
        "evaluator": {
            "type": "rtl_records",
            "artifact": artifact,
            "require_storage_classes": ["rom", "hbm"],
            "workload": "TA-QW-EOS-1",
            "require_fields": [{"field": field, "equals": True}],
        },
    }


def _rung_record(repo: Path, storage_class: str, field: str, value=True) -> dict:
    body = _record(repo, storage_class)
    body.pop("record_token_ids", None)
    body.pop("oracle", None)
    head, _, leaf = field.partition(".")
    body[head] = {leaf: value}
    return body


def _board(repo: Path) -> list[dict]:
    return [
        {"id": "G1", "kind": "terminal", "statement": "G1", "fails_when": "-", "evaluator": ROLLUP},
        _rung("G1a", "results/rtl/a.json", "coverage.ok"),
        _rung("G1b", "results/rtl/b.json", "layer.complete"),
    ]


def _write_cert(repo: Path, **over) -> None:
    body = {"certificate": {"every_issued_instance_covered": True, "uncovered_instance_count": 0}}
    body["certificate"].update(over)
    _write(repo, CERT_REL, body)


def _all_rungs(repo: Path) -> None:
    for rel, field in (("results/rtl/a.json", "coverage.ok"), ("results/rtl/b.json", "layer.complete")):
        _write(repo, rel, {"records": [_rung_record(repo, "rom", field), _rung_record(repo, "hbm", field)]})


def _rollup(repo: Path) -> dict:
    board = _board(repo)
    return gates.evaluate(board[0], board)


def test_rollup_fails_when_a_rung_fails(repo):
    _write_cert(repo)
    _write(repo, "results/rtl/a.json", {"records": [_rung_record(repo, "rom", "coverage.ok"),
                                                    _rung_record(repo, "hbm", "coverage.ok")]})
    got = _rollup(repo)
    assert got["status"] == "fail"
    assert "G1b" in got["why"]


def test_rollup_fails_when_the_certificate_is_absent(repo):
    _all_rungs(repo)
    got = _rollup(repo)
    assert got["status"] == "fail"
    assert "certificate" in got["why"]


def test_rollup_fails_when_the_certificate_leaves_instances_uncovered(repo):
    _all_rungs(repo)
    _write_cert(repo, every_issued_instance_covered=False, uncovered_instance_count=7)
    got = _rollup(repo)
    assert got["status"] == "fail"
    assert "every_issued_instance_covered" in got["why"]


def test_rollup_passes_only_with_every_rung_and_the_certificate(repo):
    _all_rungs(repo)
    _write_cert(repo)
    got = _rollup(repo)
    assert got["status"] == "pass", got["why"]


def test_rollup_naming_a_gate_that_does_not_exist_fails(repo):
    _all_rungs(repo)
    _write_cert(repo)
    board = _board(repo)
    board[0]["evaluator"] = dict(ROLLUP, requires=["G1a", "G1z"])
    got = gates.evaluate(board[0], board)
    assert got["status"] == "fail"
    assert "G1z" in got["why"]


# ---------------------------------------------------------------------------
# The configured oracle paths must resolve against the REAL artifacts in this
# repository.  A gate that fails because its field path is wrong looks exactly
# like a gate that fails because the work is not done, and the second is the
# only failure anyone should ever have to read.
# ---------------------------------------------------------------------------


def _spec_gate(gid: str) -> dict:
    body = json.loads((ROOT / "configs/gates/redesign_gates.json").read_text())
    return next(g for g in body["gates"] if g["id"] == gid)


def test_the_g1d_oracle_path_resolves_in_this_repository():
    ev = _spec_gate("G1d")["evaluator"]
    oracle = ROOT / ev["oracle"]
    assert oracle.exists(), f"{ev['oracle']} is missing"
    body = json.loads(oracle.read_text())
    node = body
    for part in ev["oracle_token_field"].split("."):
        assert isinstance(node, dict) and part in node, (
            f"G1d oracle_token_field {ev['oracle_token_field']!r} does not resolve at {part!r}"
        )
        node = node[part]
    assert isinstance(node, list) and node, "the oracle's token ids are empty"


def test_every_ladder_rung_declares_both_storage_classes_and_the_workload():
    for gid in ("G1a", "G1b", "G1c", "G1d", "G1e", "G1f"):
        ev = _spec_gate(gid)["evaluator"]
        assert ev["type"] == "rtl_records", gid
        assert sorted(ev["require_storage_classes"]) == ["hbm", "rom"], gid
        assert ev["workload"], gid
        assert ev.get("require_fields"), f"{gid} asserts nothing of its own"


def test_the_rollup_requires_every_rung_the_spec_defines():
    ev = _spec_gate("G1")["evaluator"]
    assert ev["type"] == "gate_rollup"
    body = json.loads((ROOT / "configs/gates/redesign_gates.json").read_text())
    rungs = sorted(g["id"] for g in body["gates"] if g["id"].startswith("G1") and g["id"] != "G1")
    assert sorted(ev["requires"]) == rungs, "a rung exists that the roll-up does not require"
    assert ev.get("certificate"), "the roll-up composes nothing"


def test_a_rung_cannot_pass_because_nothing_ran(repo):
    """G1f's declared fields all passed on a run of zero operations.

    configuration.reduced and structurally_identical_to_full are properties of
    a config file, and golden_injected_operation_count == 0 is satisfied
    vacuously by executing nothing at all.  A rung green because nothing ran is
    the not_evaluable defect wearing a lab coat, so the spec requires at least
    one end-to-end operation.
    """
    ev = _spec_gate("G1f")["evaluator"]
    mins = {m["field"]: m["at_least"] for m in ev.get("require_min", [])}
    assert "injection.end_to_end_operations_executed" in mins, (
        "G1f can be satisfied by a run that executed nothing"
    )
    assert mins["injection.end_to_end_operations_executed"] >= 1


def test_every_rung_requires_something_to_have_executed():
    """The provenance spine already demands positive simulated_cycles.

    This pins that no rung is exempt, so a future rung cannot be added whose
    fields are all satisfiable by an artifact describing an empty run.
    """
    body = json.loads((ROOT / "configs/gates/redesign_gates.json").read_text())
    for gate in body["gates"]:
        if not gate["id"].startswith("G1") or gate["id"] == "G1":
            continue
        ev = gate["evaluator"]
        assert ev["type"] == "rtl_records", gate["id"]
        # the shared spine in _rtl_record_problems requires
        # execution.simulated_cycles > 0 for every rung; assert the rung did
        # not opt out by declaring a different evaluator type.
        assert ev.get("require_storage_classes"), gate["id"]
