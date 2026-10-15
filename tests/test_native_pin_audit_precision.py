"""Native boundary limits apply before display rounding."""
import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools/hier_contract"))
import native_pin_audit as audit


def run_audit(tmp_path, values, kind):
    metrics = {name: {"dir": kind, "comb": False,
                      "out": value if kind == "output" else None,
                      "inp": value if kind == "input" else None}
               for name, value in values}
    with patch.object(audit.PA, "parse_lib", return_value={"cell": "test"}), \
         patch.object(audit.PA, "clock_refs", return_value={}), \
         patch.object(audit.PA, "pin_metrics", return_value=metrics):
        return audit.audit_one((tmp_path, "test", "view"))


def test_actual_capture_overrun_is_not_rounded_into_pass(tmp_path):
    result = run_audit(tmp_path, [("b2[79]", 190.01212)], "input")
    assert result["capture_ps"] == 190.0
    assert result["capture_over"] == 1
    assert not result["pass"]
    assert "190.01212" in result["fail_why"]


def test_launch_overrun_is_not_rounded_into_pass(tmp_path):
    result = run_audit(tmp_path, [("o_data", 220.01212)], "output")
    assert result["launch_ps"] == 220.0
    assert result["launch_over"] == 1
    assert not result["pass"]


def test_worst_pin_comparison_uses_full_precision(tmp_path):
    result = run_audit(tmp_path, [("worst", 190.04), ("smaller", 190.02)], "input")
    assert result["capture_pin"] == "worst"
    assert result["capture_over"] == 2
    assert not result["pass"]


def test_exact_limit_remains_accepted(tmp_path):
    assert run_audit(tmp_path, [("i", 190.0)], "input")["pass"]
    assert run_audit(tmp_path, [("o", 220.0)], "output")["pass"]
