"""FABLE-PD-QCC-0740: bind ERROR when a plan hard-core param_wrap row differs from the bound instance."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hard_core_param as H

ROW = dict(inst="u_sk", module="wrap_m", physical_inst="u_bound.u_sk", param_wrap=dict(base="skew_pipe", params={"SKEW_N": 6, "SKEW_S": 7}))


def _bound(n=6, s=7, mod="skew_pipe"):
    return f"module t(input clk);\n    {mod} #(.SKEW_N({n}), .SKEW_S({s}), .HI_PAD(18)) u_sk (\n        .clk(clk));\nendmodule\n"


def test_equal_params_pass():
    assert H.check_bound_text("T", _bound(), [ROW]) == []


def test_qcc_0740_values_are_errors():
    r = H.check_bound_text("T", _bound(8, 9), [ROW])
    assert len(r) == 2 and "SKEW_N bound 8, plan param_wrap 6" in r[0] and "SKEW_S bound 9, plan param_wrap 7" in r[1]


def test_wrong_module_missing_param_and_missing_instance():
    assert "bound module other" in H.check_bound_text("T", _bound(mod="other"), [ROW])[0]
    r = dict(ROW, param_wrap=dict(base="skew_pipe", params={"NOPE": 1}))
    assert "parameter NOPE bound None" in H.check_bound_text("T", _bound(), [r])[0]
    assert "found 0" in H.check_bound_text("T", "module t();\nendmodule\n", [ROW])[0]


def test_row_without_param_wrap_is_not_checked():
    row = {k: v for k, v in ROW.items() if k != "param_wrap"}
    assert H.check_bound_text("T", _bound(9, 9), [row]) == []
