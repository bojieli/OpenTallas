"""FAIL-CLASS 52b3512588: gen_phys with a BIND-PIN reset_tree.py older than RAW-TAP-HOLD"""
import sys, types
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys


class _P:
    def __init__(self, reset):
        self.reset = reset


def test_old_pinned_reset_tree_without_raw_tap_hold_gives_zero():
    old = types.ModuleType("reset_tree")          # a pinned reset_tree.py from before 899f9018ad2
    assert gen_phys.raw_tap_hold_pinned(old, _P({}), "t") == 0


def test_old_pin_refused_when_plan_opts_in():
    old = types.ModuleType("reset_tree")
    with pytest.raises(RuntimeError, match="predates RAW-TAP-HOLD"):
        gen_phys.raw_tap_hold_pinned(old, _P({"raw_tap_hold": {"n": 1}}), "t")


def test_current_reset_tree_is_called():
    new = types.SimpleNamespace(raw_tap_hold=lambda P, tn: 3)
    assert gen_phys.raw_tap_hold_pinned(new, _P({"raw_tap_hold": {"n": 3}}), "t") == 3
