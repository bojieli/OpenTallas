"""FLOW-GEN-1 10-28: lec.py takes the reset ports each kit DECLARES (core.json boundary_role 'reset', constraint.sdc
'# reset <ports>:'), so a reset needs no entry in the name pattern (KV-KITS-9 had to add hrst_n / hrst to it).
python3 -m pytest -q tools/die_plan/test_lec_kit_reset_ports.py"""
import json

import lec


def test_kit_reset_ports_from_core_json_and_sdc(tmp_path):
    assert lec.kit_reset_ports(tmp_path) is None
    (tmp_path / "core.json").write_text(json.dumps({"boundary_role": {"clk": "clk", "pwr_ok": "reset"}}))
    (tmp_path / "constraint.sdc").write_text("set x 1\n# reset dom_clr_n other_r: wavefront relay -> registered\n")
    assert lec.kit_reset_ports(tmp_path) == ["dom_clr_n", "other_r", "pwr_ok"]


def test_declared_reset_is_a_reset_without_a_name_rule():
    p = {"pi:rst_n[0]": 2, "pi:dom_clr_n[0]": 4, "pi:data[0]": 6}
    assert lec.reset_vars({}, p) == {1: 0}                                    # name pattern alone: dom_clr_n missed
    assert lec.reset_vars({}, p, declared=["dom_clr_n"]) == {1: 0, 2: 0}      # declared: active low by its stem
    assert lec.reset_vars({}, p, declared=None) == lec.reset_vars({}, p, declared=[])   # default unchanged


def test_env_override_still_wins(monkeypatch):
    monkeypatch.setenv("OT_LEC_RESET_PORTS", "rst_n")
    assert lec.reset_vars({}, {"pi:rst_n[0]": 2, "pi:dom_clr_n[0]": 4}, declared=["dom_clr_n"]) == {1: 0}
