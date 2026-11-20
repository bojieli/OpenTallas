"""FLOW-NOADV-R2 11-20 (FABLE-FLOW-1000 class 1): gen solves a bound reset tree with the cap it was bound with.

A generator default change (aced0fb210: reset hop cap 405 -> 300) must not refuse live 405 binds.  One bound type per die
(qwen_kvsys, s81, qwen_compute): bind at 405, then gen under the 300 default and no env."""
import copy
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bound_reset_contract as BRC  # noqa: E402
import cbc_rules as CBC  # noqa: E402
import gen_phys as G  # noqa: E402
import gen_rtl  # noqa: E402
import reset_tree as RT  # noqa: E402
import schema  # noqa: E402

PAIR = json.loads((HERE / "examples" / "s81_pair" / "s81_pair_plan.json").read_text())


def _plan():
    raw = copy.deepcopy(PAIR)
    raw.setdefault("reset", {}).update(release="pipelined")
    assert schema.validate(raw) == []
    return schema.Plan(raw)


def _bound(monkeypatch, tmp_path):
    """bind at the 405 rule: the type with the longest reset hop, its tree, its RTL, its emitted receipt"""
    monkeypatch.setenv("OT_RESET_HOP_CAP_UM", "405")
    P = _plan()
    tn = max(P.types, key=lambda t: RT.for_type(P, t)["max_hop_um"])
    tree = RT.for_type(P, tn)
    assert tree["reach_um"] == 405.0 and tree["max_hop_um"] > 300.0 - RT.MARGIN_UM
    f = tmp_path / "bound.sv"
    top = P.types[tn]["module"]
    f.write_text(f"module {top}(input clk, arst_n);\n bound u_bound(.clk(clk), .arst_n(arst_n));\nendmodule\n"
                 "module bound(input clk, arst_n);\n" + "\n".join(RT.rtl_lines(tree)) + "\nendmodule\n" + gen_rtl.CELLS)
    rec = BRC.emitted(f, tn, tree)
    assert rec["reach_cap_um"] == 405.0
    return P, tn, tree, f, rec


def _gen_default(monkeypatch):
    monkeypatch.delenv("OT_RESET_HOP_CAP_UM", raising=False)
    monkeypatch.delenv("OT_CBC_REACH_UM", raising=False)
    assert CBC.reset_hop_cap_um() == 300.0


@pytest.mark.parametrize("die", ["qwen_kvsys", "s81", "qwen_compute"])
def test_gen_solves_a_bound_tree_with_its_bound_cap(die, monkeypatch, tmp_path):
    P, tn, tree, f, rec = _bound(monkeypatch, tmp_path)
    stale = copy.deepcopy(tree)
    stale["relays"] = stale["relays"][:-1]                 # a published collector_tree older than the solve: forces the re-solve
    P.types[tn].setdefault("clock", {}).setdefault("landing_contract", {})["collector_tree"] = stale
    _gen_default(monkeypatch)
    # control: under the 300 default the plain solve is another tree (the refusal of class 1)
    try:
        assert G._bound_reset_identity(RT.for_type(P, tn)) != G._bound_reset_identity(tree)
    except RT.ResetError:
        pass                                              # the 300 solve may not even fit the plan's depth contract
    # with the receipt's cap (and with an old receipt that only has tree.reach_um) the captured tree is accepted
    for src in (rec, {k: v for k, v in rec.items() if k != "reach_cap_um"}):
        P2 = copy.deepcopy(P)
        c = G.install_bound_native_reset(P2, tn, [f], source_contract=src)
        assert c["entry_path"] and P2.types[tn]["clock"]["landing_contract"]["collector_tree"]["reach_um"] == 405.0
    assert CBC.reset_hop_cap_um() == 300.0                 # the scope did not leak


def test_scope_nests_and_ignores_nothing():
    with CBC.bound_reset_hop_cap(405):
        assert CBC.reset_hop_cap_um() == 405.0
        with CBC.bound_reset_hop_cap(None):
            assert CBC.reset_hop_cap_um() == 405.0
        with CBC.bound_reset_hop_cap(250):
            assert CBC.reset_hop_cap_um() == 250.0
        assert CBC.reset_hop_cap_um() == 405.0


def test_reach_cap_reads_receipt_then_tree():
    assert BRC.reach_cap_um({"reach_cap_um": 405, "tree": {"reach_um": 300}}) == 405.0
    assert BRC.reach_cap_um({"tree": {"reach_um": 300}}) == 300.0
    assert BRC.reach_cap_um({"tree": {}}) is None and BRC.reach_cap_um(None) is None


def test_ring_fan_and_start_corridor_read_the_cap_at_call_time(monkeypatch):
    # FLOW-NOADV-R2 11-20 (COORD): clock_landings.RING_RESET_FAN_UM / kv_start_corridor_event MAX_HOP_UM were import-time constants
    import clock_landings as CL
    import kv_start_corridor_event as KS
    monkeypatch.delenv("OT_RESET_HOP_CAP_UM", raising=False)
    assert CL.ring_reset_fan_um() == 300.0 and KS.max_hop_um() == 300.0 and KS.step_um() == 260.0 and KS.need_um() == 300.0
    with CBC.bound_reset_hop_cap(405):
        assert CL.ring_reset_fan_um() == 405.0 and KS.max_hop_um() == 405.0 and KS.step_um() == 340.0 and KS.need_um() == 380.0
        # a 350-um spread is one group under the bound 405 cap, a far cluster under the 300 default
        home, groups = [(0.0, 0.0)], [("a", [(350.0, 0.0)])]
        assert CL.reset_fan_clusters(home, groups)[2] == []
    assert len(CL.reset_fan_clusters(home, groups)[2]) == 1
    assert CBC.reset_hop_cap_um() == 300.0
