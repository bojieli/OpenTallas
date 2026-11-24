"""CORE-TAP-BUDGET 11-24: core_tap_census.py owner classes, offset-span residual and per-type summary."""
import sys
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "die_plan"))
import core_tap_census as CT  # noqa: E402
import gen_phys as GP  # noqa: E402
import schema as S  # noqa: E402


def test_owner_classes_match_gen_phys_prefixes():
    assert CT.owner_class({}) == "NONE"
    assert CT.owner_class({"budget_owner": "SIGNED:x", "insertion_ff_ps": 1}) == "SIGNED"
    assert CT.owner_class({"budget_owner": "SIGNED:x"}) == "SIGNED-noFF"
    assert CT.owner_class({"budget_owner": "parent_budget m", "insertion_ff_ps": 1}) == "parent_budget"
    assert CT.owner_class({"budget_owner": "physical/v/x_tt.lib"}).startswith("OTHER:physical/v")


def test_offset_span_core_rows_on_residual():
    # QC cbx_q10 form: a core-tap row carries its early delivery (-449.95) in the raw offset; residual = o + ins - common
    tap = dict(name="u_c.clk", kind="core", xy=[0, 0], insertion_ps=700.0, insertion_ff_ps=567.0)
    t = dict(clock=dict(core_taps="early", taps=[tap]))
    P = SimpleNamespace(types={"T": t}, die={"period_ps": 833},
                        clock={"insertion_ps": 250.0, "insertion_ff_ps": 202.5, "seam_hold": {"x": 1},
                               "tap_offset": {"per_port_ps": {"T": {"clk_c0": {"TT": -450.0, "FF": -364.5, "tol": 15.0},
                                                                    "clk_t0": {"TT": 20.0, "FF": 16.0, "tol": 25.0}}}}})
    n, w_raw, w_res, err = CT.offset_spans(GP, S, P, "T")
    assert err == "" and n == 1
    assert w_raw == 510.0                    # (20 + 25) - (-450 - 15): the window the tool applies today
    assert w_res == 60.0                     # residual 0 +/- 15 with 20 +/- 25: 45 - (-15)


def test_summary_worst_error_per_type():
    rows = [dict(die="d", type="T", placed="yes", path="legacy", owner_class="NONE", err_TT=58.65, W_extra=0.0,
                 plan_minus_contract_TT=-4.75),
            dict(die="d", type="T", placed="yes", path="legacy", owner_class="NONE", err_TT=-60.0, W_extra=0.0)]
    s = CT.summary(rows)
    assert len(s) == 1 and s[0]["err"] == -60.0 and s[0]["pmc"] == -4.75 and s[0]["n"] == 2 and s[0]["owners"] == "NONE"
