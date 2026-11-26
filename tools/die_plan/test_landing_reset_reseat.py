"""An anchored FSTART reset copy can move without changing age or other copies."""

from types import SimpleNamespace

import landing_reset_reseat as reseat


def test_local_fstart_reseat_preserves_authority_and_defers_infeasible_copy(monkeypatch, tmp_path):
    first = dict(name="fstart_0", raw="rst_rl_8", xy_um=[310.0, 60.0],
                 consumers=["u_cland_fstart_out_face"])
    unreachable = dict(name="fstart_1", raw="rst_rl_8", xy_um=[510.0, 60.0],
                       consumers=["u_cland_fstart_far"])
    unrelated = dict(name="status_2", raw="rst_rl_8", xy_um=[120.0, 80.0],
                     consumers=["u_cland_up_c"])
    clk = dict(reset_tree_anchor={"relays": {"rst_rl_8": {"depth": 7}}},
               landing_local_resets=[first, unreachable, unrelated],
               landing_contract={"pins": [
                   {"name": "cland_fstart_out_out_face", "xy_um": [330, 61]},
                   {"name": "cland_fstart_out_far", "xy_um": [565, 61]},
               ]})
    plan = SimpleNamespace(types={"t": dict(outline_um=[600, 200], clock=clk)})
    tree = {"relays": [{"q": "rst_rl_8", "name": "u_rrl_8", "xy": [70.0, 60.0]}]}
    monkeypatch.setattr(reseat.reset_tree, "for_type", lambda *_: tree)
    monkeypatch.setattr(reseat.reset_tree, "relay_cell", lambda *_: "ot_dp_rrelay_nl")
    monkeypatch.setattr(reseat.reset_anchor, "resolve", lambda *_: {"remaps": []})
    monkeypatch.setattr(reseat.reset_anchor, "ported", lambda *_: set())
    monkeypatch.setattr(reseat.schema, "tap_grid", lambda *_: [])

    fixed, still_bad = reseat.reseat(plan, "t", tmp_path)
    assert fixed["status"] == "reseated"
    assert fixed["depth"] == 7 and first["raw"] == "rst_rl_8"
    assert fixed["incoming_cap"] == 180 and fixed["incoming_um"] <= 180
    assert fixed["outgoing_um"] <= fixed["outgoing_cap"]
    assert first["xy_um"] != [310, 60]
    assert still_bad["status"] == "no legal site for existing raw relay and consumer reach"
    assert unreachable["xy_um"] == [510, 60]
    assert unrelated["xy_um"] == [120, 80]
    assert reseat.reseat(plan, "t", tmp_path)[0]["status"] == "within reach"
