"""PRE-MODE-1124: plan_gate_pre says whether the bound-RTL checks ran or were downgraded."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plan_gate_pre as G  # noqa: E402


def test_plan_only_names_the_downgraded_checks():
    m = G.pre_mode(None)
    assert m.startswith("LIST PRE-MODE plan-only: 4 bound checks downgraded (") and "MACROGHOST" in m and "SEATMATCH" in m


def test_bound_when_error_free_bind_report(tmp_path):
    (tmp_path / "bind_report.json").write_text(json.dumps({"errors": 0}))
    assert G.pre_mode(str(tmp_path)) == "LIST PRE-MODE bound"


def test_failed_bind_is_plan_only(tmp_path):
    (tmp_path / "bind_report.json").write_text(json.dumps({"errors": 3}))
    assert G.pre_mode(str(tmp_path)).startswith("LIST PRE-MODE plan-only")


def test_skipped_check_not_counted():
    assert "3 bound checks" in G.pre_mode(None, skip=("MACROGHOST",))
