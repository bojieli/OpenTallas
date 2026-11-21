"""RESET-RELAY-GEN-R3 11-21: reset.root_entry_negedge (launch-side lockup on the root entry) + the 150 ps auto rule.
python3 -m pytest -q tools/die_plan/test_root_entry_negedge.py"""
import copy
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import reset_tree as RT  # noqa: E402
import root_entry_scan as RS  # noqa: E402
import schema  # noqa: E402

PAIR = json.loads((HERE / "examples" / "s81_pair" / "s81_pair_plan.json").read_text())


def piped(raw, **kw):
    raw = copy.deepcopy(raw)
    raw.setdefault("reset", {}).update(release="pipelined", **kw)
    return raw


T60_RPT = """Startpoint: u_bound.u_rst_in/q$_DFF_P_
            (rising edge-triggered flip-flop clocked by clk)
Endpoint: u_bound.u_rrl_167/state$_DFF_P_
Path Group: clk
Path Type: min

                 13.48    0.58   67.34 ^ u_bound.u_rst_in/q$_DFF_P_/CLK (DFFHQNx1_ASAP7_75t_R)
                 18.40    3.61  306.74 ^ u_bound.u_rrl_167/state$_DFF_P_/CLK (DFFHQNx1_ASAP7_75t_R)
                                -158.81   slack (VIOLATED)
"""


def test_auto_rule_t60_numbers_fire_and_150ps_boundary():
    lc = RS.root_hop_latencies(T60_RPT)
    assert lc == (67.34, 306.74) and RS.fires(*lc)
    assert not RS.fires(100.0, 250.0) and RS.fires(100.0, 250.1)
    assert RS.root_hop_latencies(T60_RPT.replace("Path Type: min", "Path Type: max")) is None


def test_root_entry_negedge_cell_default_off_and_exclusions():
    raw = piped(PAIR)
    tn = sorted(raw["partition_types"])[0]
    base = RT.rtl_lines(RT.for_type(schema.Plan(raw), tn))
    assert any("ot_dp_rrelay u_rst_in" in ln for ln in base) or any("u_rst_in" in ln for ln in base)
    on = copy.deepcopy(raw)
    on["partition_types"][tn].setdefault("reset", {})["root_entry_negedge"] = True
    assert schema.validate(on) == []
    P = schema.Plan(on)
    T = RT.for_type(P, tn)
    lines = RT.rtl_lines(T)
    assert T["root_entry_negedge"] is True
    assert any("ot_dp_rrelay_nl u_rst_in" in ln for ln in lines)
    assert T["depth"] == RT.for_type(schema.Plan(raw), tn)["depth"]          # 0 cycles
    bad = copy.deepcopy(on)
    bad["partition_types"][tn]["reset"]["root_entry_negedge"] = "yes"
    with pytest.raises(Exception):
        RT.for_type(schema.Plan(bad), tn)


def test_auto_rule_applies_only_to_measured_firing_types():
    raw = piped(PAIR)
    a, b = sorted(raw["partition_types"])[:2]
    got = RS.apply(raw, {a: dict(launch_ps=67.34, capture_ps=306.74), b: dict(launch_ps=10, capture_ps=100), "nope": dict(launch_ps=0, capture_ps=999)})
    assert got == {a: 239.4} and raw["partition_types"][a]["reset"]["root_entry_negedge"] is True
    assert "root_entry_negedge" not in raw["partition_types"][b].get("reset", {})
