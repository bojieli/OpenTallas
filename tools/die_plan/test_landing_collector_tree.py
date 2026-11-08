"""S81-OTHERFAIL-1 (11-07): RTL collectors, their verify and landing_place.tcl walk ONE tree (the plan contract's)."""
import landing_collector as LC

PLAN = {"relays": [{"q": "rst_rl_45", "d": "rst_root_n", "xy": [100.0, 400.0]},
                   {"q": "rst_n_t28", "d": "rst_rl_45", "xy": [8.2, 460.6]}], "root": [300.0, 300.0]}
STALE = {"relays": [{"q": "rst_rl_58", "d": "rst_root_n", "xy": [1.0, 1.0]},
                    {"q": "rst_n_t28", "d": "rst_rl_58", "xy": [8.2, 460.6]}], "root": [300.0, 300.0]}


def typ(tree):
    return {"clock": {"landing_contract": {"collector_tree": tree}}}


def test_plan_contract_tree_wins_over_a_stale_table_copy():
    assert LC.effective_tree(typ(PLAN), STALE) is PLAN


def test_no_contract_tree_keeps_the_table_tree():
    assert LC.effective_tree({}, STALE) is STALE
    assert LC.effective_tree(None, STALE) is STALE


def test_hard_trees_and_inactive_types_are_untouched():
    hard = dict(STALE, hard=True)
    assert LC.effective_tree(typ(PLAN), hard) is hard
    assert LC.effective_tree(typ(dict(PLAN, hard=True)), STALE) is STALE
    assert LC.effective_tree(typ(PLAN), None) is None


def test_chain_follows_the_plan_tree():
    body = "    wire rst_rl_45;\n    wire rst_n_t28;\n    wire rr_t28;\n"
    src = [dict(name="child0", node="rst_n_t28", ready="r0", fault="f0")]
    out = LC.build_local(LC.effective_tree(typ(PLAN), STALE), src, body)
    names = [i["name"] for i in out["instances"] if i["module"] == "ot_dp_landing_collect"]
    assert "u_cland_collect_rst_rl_45" in names and "u_cland_collect_rst_rl_58" not in names
