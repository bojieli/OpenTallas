"""TOK-S81-1: per-frame landing-K gate at bind time (check_frame_lk.py)."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_frame_lk as C  # noqa: E402

REPO = HERE.parents[3]
MODELS = """module col_h9_l4_lp_asb_x #(parameter INSTANCE = "x") ();
    col_h9_l4_lp_r0 #(.INSTANCE(INSTANCE), .LK({4{3'd2}})) u_r0 (.clk(ck_r0));
    col_h9_l4_lp_r1 #(.INSTANCE(INSTANCE), .LK({4{3'd2}})) u_r1 (.clk(ck_r1));
endmodule
"""
PLAN = {"schema": "opentallas.s81.frame_lk.v1",
        "rows": {"u_f_0L01": {"K": 2, "legal_E": [1, 2, 3]}, "u_f_0L02": {"K": 2, "legal_E": [1, 2, 3]}}}
TOP = ("  col_h9_l4_lp_asb_x #(.INSTANCE(\"u_f_0L01\")) u_f_0L01 (.ck_r0(a), .x(b));\n"
       "  col_h9_l4_lp_asb_x #(.INSTANCE(\"u_f_0L02\")) u_f_0L02 (.ck_r0(a), .x(b));\n")


def test_lanes():
    assert C.lanes("{4{3'd2}}") == [2, 2, 2, 2]
    assert C.lanes("12'h492") == [2, 2, 2, 2]
    assert C.lanes("12'hb6d") == [5, 5, 5, 5]
    assert C.lanes("LKX") is None


def test_pass():
    errs, rows = C.check(TOP, MODELS, PLAN)
    assert errs == [] and len(rows) == 4


def test_wrapper_mismatch_fails():
    errs, _ = C.check(TOP, MODELS.replace("3'd2}})) u_r1", "3'd5}})) u_r1"), PLAN)
    assert len(errs) == 2 and all(".r1: lanes [5, 5, 5, 5]" in e for e in errs)


def test_die_override_wins_and_fails():
    top = TOP.replace("u_f_0L02 (.ck_r0(a)", "u_f_0L02 (.lk(12'hb6d), .ck_r0(a)")
    errs, rows = C.check(top, MODELS, PLAN)
    assert errs and any(r["source"] == "die_top_override" and not r["ok"] for r in rows)


def test_missing_row_and_frame_fail():
    plan = json.loads(json.dumps(PLAN))
    plan["rows"].pop("u_f_0L02")
    plan["rows"]["u_f_9L99"] = {"K": 2, "legal_E": [2]}
    errs, _ = C.check(TOP, MODELS, plan)
    assert any("no frame_lk row" in e for e in errs) and any("not in the die top" in e for e in errs)


def test_illegal_K_fails():
    plan = json.loads(json.dumps(PLAN))
    plan["rows"]["u_f_0L01"]["legal_E"] = [1, 3]
    errs, _ = C.check(TOP, MODELS, plan)
    assert any("u_f_0L01" in e for e in errs)


def test_repo_die_b178_passes():
    b = REPO / "physical/die_plan/s81/bind"
    errs, rows = C.check((b / "inputs/die_b178.v").read_text(), (b / "models/s81_asb_models.sv").read_text(),
                         json.loads((REPO / "results/s81_unblock3_1027/fi_seam/frame_lk.json").read_text()))
    assert errs == [] and len({r["inst"] for r in rows}) == 72
