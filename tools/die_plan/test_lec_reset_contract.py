"""COORD 10-27: a reset window above 4 edges only from a proven, receipted die reset contract; fail closed."""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lec


def _contract(tmp_path, edges=16, assert_edges=16, verdict="PASS", mutant="CAUGHT", modules=("top_c",), sha=None):
    r = tmp_path / "reset_proof.log"
    r.write_text("sat -tempinduct: SUCCESS  NMIN=16\n")
    c = dict(schema="opentallas.reset_contract.v1", die="kv", edges=edges, modules=list(modules),
             proof=dict(verdict=verdict, assert_edges=assert_edges, mutant=mutant, receipt=r.name,
                        receipt_sha256=sha or hashlib.sha256(r.read_bytes()).hexdigest()))
    (tmp_path / "reset_contract.json").write_text(json.dumps(c))
    return r


def test_no_contract_refuses_longer_window(tmp_path):
    env = {"OT_LEC_RESET_CYCLES": "16"}
    rep = lec.reset_contract_gate(tmp_path, "top_c", env)
    assert env["OT_LEC_RESET_CYCLES"] == "4" and rep["used"] == 4 and "refused" in rep


def test_shorter_window_without_contract_is_allowed(tmp_path):
    env = {"OT_LEC_RESET_CYCLES": "2"}
    assert lec.reset_contract_gate(tmp_path, "top_c", env)["used"] == 2


def test_valid_contract_gives_declared_length(tmp_path):
    _contract(tmp_path)
    env = {}
    rep = lec.reset_contract_gate(tmp_path, "top_c", env)
    assert env["OT_LEC_RESET_CYCLES"] == "16" and "refused" not in rep


def test_request_above_proven_is_refused(tmp_path):
    _contract(tmp_path, edges=16, assert_edges=16)
    env = {"OT_LEC_RESET_CYCLES": "20"}
    assert lec.reset_contract_gate(tmp_path, "top_c", env)["used"] == 4


def test_mutants_fail_closed(tmp_path):
    for kw in (dict(verdict="FAIL"), dict(mutant="MISSED"), dict(modules=("other",)), dict(sha="0" * 64),
               dict(assert_edges=2)):
        _contract(tmp_path, **kw)
        env = {}
        rep = lec.reset_contract_gate(tmp_path, "top_c", env)
        assert env["OT_LEC_RESET_CYCLES"] in ("4", "2"), kw
        if "assert_edges" not in kw:
            assert "refused" in rep, kw


def test_tampered_receipt_fails_closed(tmp_path):
    r = _contract(tmp_path)
    r.write_text("sat -tempinduct: FAIL\n")
    env = {}
    assert "refused" in lec.reset_contract_gate(tmp_path, "top_c", env) and env["OT_LEC_RESET_CYCLES"] == "4"
