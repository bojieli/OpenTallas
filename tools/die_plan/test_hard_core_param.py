"""FABLE-PD-QCC-0740: bind ERROR when a plan hard-core param_wrap row differs from the bound instance."""
import sys
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hard_core_param as H


def _plan(params):
    return dict(partitions=[dict(name="p0", type="T")],
                partition_types=dict(T=dict(hard_cores=[dict(inst="u_sk", module="wrap_m", physical_inst="u_bound.u_sk",
                                                             param_wrap=dict(base="skew_pipe", params=params))])))


def _cell(module="skew_pipe", params=None, ytype="$paramod$x"):
    return NS(path="p0.u_sk", module=module, ytype=ytype, params=params if params is not None else {})


def _run(plan, cells, defaults=None):
    return H.mismatches(plan, cells, lambda path: "p0", lambda path: "u_sk", defaults or {})


def test_equal_params_pass_including_module_defaults():
    assert _run(_plan({"SKEW_N": 6, "SKEW_S": 7}), [_cell(params={"SKEW_N": 6, "SKEW_S": 7})]) == []
    assert _run(_plan({"SKEW_N": 6}), [_cell(params={})], {("$paramod$x", "skew_pipe"): {"SKEW_N": 6}}) == []


def test_qcc_0740_values_are_errors():
    r = _run(_plan({"SKEW_N": 6, "SKEW_S": 7}), [_cell(params={"SKEW_N": 8, "SKEW_S": 9})])
    assert len(r) == 2 and "SKEW_N as-built 8, plan param_wrap 6" in r[0] and "SKEW_S as-built 9" in r[1]


def test_missing_param_and_wrong_module_are_errors():
    assert len(_run(_plan({"SKEW_N": 6}), [_cell(params={})])) == 1
    r = _run(_plan({"SKEW_N": 6}), [_cell(module="other", params={"SKEW_N": 6})])
    assert len(r) == 1 and "as-built module other" in r[0]


def test_row_without_param_wrap_is_not_checked():
    plan = _plan({"SKEW_N": 6}); del plan["partition_types"]["T"]["hard_cores"][0]["param_wrap"]
    assert _run(plan, [_cell(params={"SKEW_N": 9})]) == []
