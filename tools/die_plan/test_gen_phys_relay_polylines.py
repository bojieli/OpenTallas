"""FIX-RELAYPOLY 11-14: plan partition_types.<t>.relay_polylines -> OT_RELAY_POLY_FILE lines for relay_mid.tcl."""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys

ENT = {"group_re": "u_y_rt_20a_", "sink": "u_r1.u_n20.a", "polyline_um": [[663, 1120], [663, 1190], [1335, 1190], [1335, 1024]], "max_hop_um": 405}


def plan(t):
    return SimpleNamespace(types={"t": t}, raw={"partition_types": {"t": t}}, budgets={})


def test_absent_is_unchanged(tmp_path, monkeypatch):
    monkeypatch.delenv("OT_RELAY_POLY", raising=False)
    assert gen_phys.write_relay_polylines(plan({}), "t", tmp_path) == 0
    assert not (tmp_path / "relay_polylines.txt").exists() and not gen_phys._relay_poly_on(plan({}), "t")


def test_entries_become_waypoint_file(tmp_path):
    P = plan({"relay_polylines": [ENT, dict(ENT, group_re="u_y_rt_20b_")]})
    assert gen_phys._relay_poly_on(P, "t") and gen_phys.write_relay_polylines(P, "t", tmp_path) == 2
    lines = (tmp_path / "relay_polylines.txt").read_text().splitlines()
    assert lines[0] == "re:u_y_rt_20a_ 663 1120 663 1190 1335 1190 1335 1024" and lines[1].startswith("re:u_y_rt_20b_ ")


def test_env_gate_alone_is_auto_path(monkeypatch):
    monkeypatch.setenv("OT_RELAY_POLY", "1")
    assert gen_phys._relay_poly_on(plan({}), "t") and not gen_phys._relay_polylines(plan({}), "t")


def test_bad_entry_is_rejected():
    with pytest.raises(SystemExit):
        gen_phys._relay_polylines(plan({"relay_polylines": [{"group_re": "x", "polyline_um": []}]}), "t")


def test_single_point_soft_head_entry(tmp_path):
    P = plan({"relay_polylines": [{"group_re": "y_rt_15a_", "polyline_um": [[630.0, 798.0]], "max_hop_um": 405}]})
    assert gen_phys.write_relay_polylines(P, "t", tmp_path) == 1
    assert (tmp_path / "relay_polylines.txt").read_text() == "re:y_rt_15a_ 630 798\n"
