"""DIE-HEAD-44 (COORD 10-30): the HEAD die reset contract (physical/die_plan/s81_head/reset_contract.json) is accepted
by lec.reset_contract_gate for its listed HEAD tops at 64 edges, its receipt records bench PASS + both mutants caught,
and an unlisted top stays at the 4-edge default."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lec

REPO = Path(__file__).resolve().parents[2]
C = REPO / "physical/die_plan/s81_head/reset_contract.json"


def test_head_contract_accepts_listed_tops():
    for top in ("ot_s81hd_host_ep", "ot_s81hd_ctl", "ot_s81hd_lep_pair", "ot_s81_kp4_dchn"):
        env = {"OT_LEC_RESET_CONTRACT": str(C)}
        rep = lec.reset_contract_gate(REPO, top, env)
        assert "refused" not in rep and rep["used"] == 64 and env["OT_LEC_RESET_CYCLES"] == "64", rep


def test_head_contract_refuses_unlisted_top():
    env = {"OT_LEC_RESET_CONTRACT": str(C)}
    rep = lec.reset_contract_gate(REPO, "not_a_head_core", env)
    assert rep["used"] == 4 and "refused" in rep


def test_head_receipt_records_pass_and_caught_mutants():
    c = json.loads(C.read_text())
    txt = (C.parent / c["proof"]["receipt"]).read_text()
    assert "HEADRST_PASS HOLD=64 MUT=0" in txt
    assert "HEADRST_FAIL HOLD=61 MUT=0" in txt and "HEADRST_FAIL HOLD=64 MUT=1" in txt
    assert "min_relay_known_low=66 min_rgate_known_low=66" in txt
