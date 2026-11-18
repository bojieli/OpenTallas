"""LOCAL-RESET-RAW-1 (S81-SERDES-GEN 11-17, FABLE-PD-S81-2100 finding 2): landing_local_resets raw names are checked against the
regenerated relay set and re-picked by site when a tap event renumbered them."""
import clock_landings as CL

RTL = """
    ot_dp_rrelay u_a (.clk(clk), .d(x), .q(rst_rl_5));  // depth 3 @ (100.0, 200.0)
    ot_dp_rrelay u_b (.clk(clk), .d(x), .q(rst_rl_6));  // depth 3 @ (900.0, 200.0)
    ot_dp_rrelay u_c (.clk(clk), .d(x), .q(rst_rl_7));  // depth 4 @ (110.0, 210.0)
    assign rst_o_p = rst_rl_6;
"""


def test_bound_relay_sites_parse():
    assert CL.bound_relay_sites(RTL) == {"rst_rl_5": (3, (100.0, 200.0)), "rst_rl_6": (3, (900.0, 200.0)), "rst_rl_7": (4, (110.0, 210.0))}
    assert CL.bound_relay_sites("no relays here") == {}


def _pick(raw, xy, need, relays=None, ported=frozenset()):
    return CL.pick_local_reset_raw(raw, xy, need, relays if relays is not None else CL.bound_relay_sites(RTL), set(ported), 405.0)


def test_valid_name_is_kept():
    assert _pick("rst_rl_5", (120.0, 190.0), 3) == ("rst_rl_5", None)


def test_vanished_name_is_repicked_by_site():                       # serdes t1: rst_rl_170 no longer exists
    assert _pick("rst_rl_170", (120.0, 190.0), 3) == ("rst_rl_5", "rst_rl_170")


def test_far_name_is_repicked_to_a_relay_within_reach():            # serdes t15: rst_rl_244 hopped 690 um
    relays = CL.bound_relay_sites(RTL)
    relays["rst_rl_244"] = (3, (790.0, 190.0))
    assert _pick("rst_rl_244", (100.0, 200.0), 3, relays) == ("rst_rl_5", "rst_rl_244")


def test_wrong_depth_and_ported_relays_are_never_taken():
    assert _pick("rst_rl_7", (110.0, 210.0), 3) == ("rst_rl_7", None)             # existing wrong-depth name: kept, the caller fails closed
    assert _pick("rst_rl_gone", (880.0, 200.0), 3, ported={"rst_rl_6"}) == ("rst_rl_gone", None)   # the only near relay is ported: not taken


def test_nothing_in_reach_keeps_the_plans_choice_and_empty_set_is_a_noop():
    assert _pick("rst_rl_5", (3000.0, 3000.0), 3) == ("rst_rl_5", None)           # valid name, nothing nearer in reach: keep
    assert CL.pick_local_reset_raw("rst_rl_9", (0, 0), 3, {}, set(), 405.0) == ("rst_rl_9", None)


def test_renumbering_does_not_change_the_picked_site():
    old = CL.bound_relay_sites(RTL)
    new = {f"rst_rl_{int(q.split('_')[-1]) + 100}": v for q, v in old.items()}   # +taps renumber every relay
    raw_old, _ = CL.pick_local_reset_raw("rst_rl_5", (120.0, 190.0), 3, old, set(), 405.0)
    raw_new, was = CL.pick_local_reset_raw(raw_old, (120.0, 190.0), 3, new, set(), 405.0)
    assert was == "rst_rl_5" and new[raw_new][1] == old[raw_old][1]


def test_writeback_rewrites_only_matching_rows(tmp_path):
    import json
    import local_reset_writeback as W
    plan = {"partition_types": {"t1": {"clock": {"landing_local_resets": [
        {"name": "a", "raw": "rst_rl_170"}, {"name": "b", "raw": "rst_rl_9"}]}}, "t2": {"clock": {}}}}
    rec = {"t1": [{"name": "a", "was": "rst_rl_170", "raw": "rst_rl_5"}, {"name": "b", "was": "rst_rl_1", "raw": "rst_rl_2"}],
           "tx": [{"name": "a", "was": "x", "raw": "y"}]}
    assert W.apply(plan, rec) == 1
    assert [r["raw"] for r in plan["partition_types"]["t1"]["clock"]["landing_local_resets"]] == ["rst_rl_5", "rst_rl_9"]
    p, r, o = tmp_path / "p.json", tmp_path / "r.json", tmp_path / "o.json"
    p.write_text(json.dumps({"partition_types": {"t1": {"clock": {"landing_local_resets": [{"name": "a", "raw": "rst_rl_170"}]}}}}))
    r.write_text(json.dumps({"t1": [{"name": "a", "was": "rst_rl_170", "raw": "rst_rl_5"}]}))
    assert W.main(["x", str(p), str(r), str(o)]) == 0
    assert json.loads(o.read_text())["partition_types"]["t1"]["clock"]["landing_local_resets"][0]["raw"] == "rst_rl_5"
