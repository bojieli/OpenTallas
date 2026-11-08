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


def _kit(tmp_path, top="top_c"):
    (tmp_path / "config.mk").write_text(f"export DESIGN_NAME = {top}\nexport VERILOG_FILES = rtl/x.v\n")
    return tmp_path


def test_listed_top_without_receipt_is_a_flow_error(tmp_path):
    """KW-FIX-35-RC 11-08 (S81 bksel vJ/vK): a kit copy kept reset_contract.json and dropped reset_contract/receipt.txt;
    LEC refused the contract and quietly proved at 4 edges (30 false m_ra differences).  The gate now flags it and check()
    stops with a FLOW ERROR before any proof, never a 4-edge verdict."""
    r = _contract(_kit(tmp_path))
    r.unlink()
    rep = lec.reset_contract_gate(tmp_path, "top_c", {})
    assert rep["used"] == 4 and "receipt missing" in rep["flow_error"] and "top_c" in rep["flow_error"]
    rec = lec.check(tmp_path, out=tmp_path / "lec")
    assert rec["verdict"] == "ERROR" and "FLOW reset contract receipt missing" in rec["reason"]
    assert "NOT EQUIVALENT" not in rec["reason"]          # kit_wave must not class it as an RTL verdict
    assert rec["reset_contract"]["flow_error"]
    assert json.loads((tmp_path / "lec/lec.json").read_text())["verdict"] == "ERROR"


def test_listed_top_with_changed_receipt_is_a_flow_error(tmp_path):
    r = _contract(_kit(tmp_path))
    r.write_text("edited\n")
    rec = lec.check(tmp_path, out=tmp_path / "lec")
    assert rec["verdict"] == "ERROR" and "sha256 mismatch" in rec["reason"]


def test_unlisted_top_or_no_contract_keeps_the_default_without_error(tmp_path):
    r = _contract(tmp_path, modules=("other",))
    r.unlink()
    rep = lec.reset_contract_gate(tmp_path, "top_c", {})
    assert rep["used"] == 4 and "flow_error" not in rep
    (tmp_path / "reset_contract.json").unlink()
    assert "flow_error" not in lec.reset_contract_gate(tmp_path, "top_c", {})
