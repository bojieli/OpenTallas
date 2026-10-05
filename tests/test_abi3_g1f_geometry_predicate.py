"""The G1f geometry-predicate classifier must be able to say the opposite.

``tools/build_abi3_g1f_geometry_predicate.py`` decides, from a sweep of the two
geometry-bearing engines, whether a refusal is a capacity bound or an exact-set
membership test.  That verdict is load-bearing for G1f's ``geometry_port_decision``
-- a capacity bound would mean the reduced configuration should be chosen inside
it and no RTL owes anything -- so the classifier needs a negative control: fed a
sweep that really does describe a bound, it must say bound, and fed one that
really is affine, it must say affine.  A classifier that only ever prints one
verdict measures nothing.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_SPEC = importlib.util.spec_from_file_location(
    "build_abi3_g1f_geometry_predicate",
    ROOT / "tools/build_abi3_g1f_geometry_predicate.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(_MODULE)

classify = _MODULE.classify
linear_in = _MODULE.linear_in

SWEPT = [1, 8, 16, 64, 127, 128, 129, 256, 1024, 4095, 4096, 4097, 8192]


def test_an_isolated_admission_set_is_not_explained_by_any_bound() -> None:
    verdict = classify(SWEPT, [128, 4096])
    assert verdict["shape"] == "exact_set_membership"
    assert verdict["consistent_with_upper_bound"] is None
    assert verdict["consistent_with_lower_bound"] is None
    assert verdict["consistent_with_interval"] is None
    bracket = verdict["each_admitted_value_bracketed"]
    assert bracket["128"]["next_lower_admitted"] is False
    assert bracket["128"]["next_higher_admitted"] is False
    assert bracket["4096"]["next_lower_admitted"] is False
    assert bracket["4096"]["next_higher_admitted"] is False


def test_a_real_upper_bound_is_reported_as_a_bound() -> None:
    """The negative control: the classifier must not call a capacity a whitelist."""
    admitted = [value for value in SWEPT if value <= 256]
    verdict = classify(SWEPT, admitted)
    assert verdict["consistent_with_upper_bound"] == 256
    assert verdict["shape"] == "interval"


def test_a_real_lower_bound_is_reported_as_a_bound() -> None:
    admitted = [value for value in SWEPT if value >= 1024]
    verdict = classify(SWEPT, admitted)
    assert verdict["consistent_with_lower_bound"] == 1024
    assert verdict["shape"] == "interval"


def test_a_contiguous_run_is_an_interval_and_not_a_whitelist() -> None:
    verdict = classify([1, 2, 4, 8, 16, 32, 64], [8, 16, 32])
    assert verdict["consistent_with_interval"] == [8, 32]
    assert verdict["shape"] == "interval"
    assert verdict["consistent_with_upper_bound"] is None
    assert verdict["consistent_with_lower_bound"] is None


def test_a_single_admitted_value_is_not_called_an_interval() -> None:
    verdict = classify([1, 2, 4, 8], [4])
    assert verdict["shape"] == "single_value"


def test_affine_traffic_is_recognised_and_non_affine_traffic_is_refused() -> None:
    affine = linear_in([(8, 69632), (16, 135168), (17, 143360), (32, 266240)])
    assert affine["affine"] is True
    assert affine["worst_residual"] == 0
    assert affine["slope"] == 8192
    assert affine["intercept"] == 4096

    bent = linear_in([(8, 69632), (16, 135168), (32, 266241)])
    assert bent["affine"] is False
    assert bent["worst_residual"] > 0
