"""C-DIECLOCK-TRUNK-UNPINNED tree_eco: pinned base nodes (outside the re-sited outlines, legal base xy) keep xy / parent /
level / parity; core-tap detach only touches re-sited types; meta.trunk_pin records the kept set."""
import tree_eco as E
from test_tree_eco import M, Site, base_tree

ALL = {0, 1, 2, 3, 4}


def test_pin_set_is_legal_base_xy_outside_resite_boxes():
    xy = {0: (0.0, 0.0), 1: (100.0, 0.0), 2: (100.0, 70.0), 3: (500.0, 0.0)}
    pin = E.trunk_pin_set(xy, Site((60.0, 80.0)), [(400.0, -10.0, 600.0, 10.0)])
    assert pin == {0, 1}            # 2: base xy illegal (the eco may legalise it); 3: inside a re-sited outline


def test_pinned_stranded_leaf_keeps_its_legal_base_xy():
    b = base_tree()
    b["taps"][0]["xy"] = [100.0, 90.0]              # leaf 2 sits 40 um below its tap
    cur = [("a", "clk_t1", 100.0, 90.0), ("a", "clk_t2", 150.0, 0.0), ("a", "clk_t3", 100.0, -50.0)]
    t0, _ = E.eco(b, cur, Site(), M, {"a": "r"})
    assert (t0["nodes"]["2"]["x"], t0["nodes"]["2"]["y"]) == (100.0, 90.0)       # unpinned: resited onto the tap
    t, r = E.eco(b, cur, Site(), M, {"a": "r"}, pin=ALL)
    n2 = t["nodes"]["2"]
    assert (n2["x"], n2["y"]) == (100.0, 50.0) and n2["physical_leg"] == b["nodes"]["2"]["physical_leg"]
    assert r["counts"]["resited_leaves"] == 0 and r["counts"]["pinned"] == 5 and r["counts"]["pin_restored"] == 0


def test_moved_tap_does_not_move_a_pinned_leaf():
    b = base_tree()
    cur = [("a", "clk_t1", 100.0, 50.0), ("a", "clk_t2", 160.0, 0.0), ("a", "clk_t3", 100.0, -50.0)]
    t, r = E.eco(b, cur, Site(), M, {"a": "r"}, pin=ALL)
    assert r["attached"][0]["how"] == "hang"
    assert "3" not in t["nodes"] and t["meta"]["trunk_pin"]["pruned"] == [3]
    for i in ("0", "1", "2", "4"):
        assert (t["nodes"][i]["x"], t["nodes"][i]["y"]) == (b["nodes"][i]["x"], b["nodes"][i]["y"])
    rec = t["meta"]["trunk_pin"]["nodes"]
    assert set(rec) == {"0", "1", "2", "4"} and rec["2"] == [100.0, 50.0, 1, 2, 0]
    _, rn = E.eco(b, cur, Site(), M, {"a": "r"}, near_um=20.0, pin=ALL)
    assert rn["counts"]["slid"] == 0                              # NEAR never slides a pinned leaf
    t1, _ = E.eco(b, cur, Site(), M, {"a": "r"}, pin={0, 1, 2, 4})   # leaf 3 re-sited: reused as before
    assert (t1["nodes"]["3"]["x"], t1["nodes"]["3"]["y"]) == (160.0, 0.0)


def test_pinned_parity_is_kept_on_a_relaid_leg():
    b = base_tree()
    b["nodes"]["3"].update(x=300.0, _relaid=True)        # 200 um leg the kit re-lays: natural layout flips parity
    b["nodes"]["3"].pop("physical_leg")
    b["taps"][1]["xy"] = [300.0, 0.0]
    cur = [("a", "clk_t1", 100.0, 50.0), ("a", "clk_t2", 300.0, 0.0), ("a", "clk_t3", 100.0, -50.0)]
    t0, _ = E.eco(b, cur, Site(), M, {"a": "r"})
    assert t0["nodes"]["3"]["inv_parity"] != b["nodes"]["3"]["inv_parity"]
    t, _ = E.eco(b, cur, Site(), M, {"a": "r"}, pin=ALL)
    assert t["nodes"]["3"]["inv_parity"] == b["nodes"]["3"]["inv_parity"]     # the kit's fix_parity owns that leg


def core_base():
    b = base_tree()
    b["taps"][2]["tap"] = "clk_c0"; b["taps"][2]["port"] = "t_a__clk_c0"
    cur = [("a", "clk_t1", 100.0, 50.0), ("a", "clk_t2", 150.0, 0.0), ("a", "clk_c0", 100.0, -50.0)]
    return b, cur


def test_core_detach_only_on_resite_types():
    b, cur = core_base()
    kw = dict(core_off={("a", "clk_c0"): -30.0}, core_tol_ps=10.0)
    _, r = E.eco(b, cur, Site(), M, {"a": "r"}, {"a": "lep"}, resite_types=["tile"], **kw)
    assert r["core_detached"] == [] and r["counts"]["matched"] == 3          # unchanged type: core leaf kept
    _, r = E.eco(b, cur, Site(), M, {"a": "r"}, {"a": "tile"}, resite_types=["tile"], **kw)
    assert [x["port"] for x in r["core_detached"]] == ["clk_c0"]
    _, r = E.eco(b, cur, Site(), M, {"a": "r"}, pin=ALL, **kw)
    assert r["core_detached"] == []                                          # a pinned core leaf is never re-hung


def test_pinned_chain_under_a_flipped_parent_is_relaid():
    nodes = {0: dict(id=0, x=0.0, y=0.0, parent=None, level=0, kids=[1], inv_parity=0),
             1: dict(id=1, x=200.0, y=0.0, parent=0, level=1, kids=[2], inv_parity=1, _relaid=True),   # re-sited, flips
             2: dict(id=2, x=200.0, y=100.0, parent=1, level=2, kids=[], inv_parity=0, physical_leg=dict(chain=[], delay_ps=1.0))}
    base = {0: 0, 1: 1, 2: 0}
    E.repair_parity(nodes, base, lambda a, b: 1, pinned={0, 2})   # nrep 1: node 1 flips to 0
    assert nodes[1]["inv_parity"] == 0
    assert nodes[2]["inv_parity"] == 0 and "physical_leg" not in nodes[2]       # kit re-lays it, fix_parity solves parity


def test_balance_never_detaches_a_pinned_leaf():
    b = base_tree()
    cur = [("a", "clk_t1", 100.0, 50.0), ("a", "clk_t2", 150.0, 0.0), ("a", "clk_t3", 100.0, -50.0)]
    cal = dict(node={0: 0.0, 1: 30.0}, leg=(0.0, 1.0), tap={("a", "clk_t1"): 50.0, ("a", "clk_t2"): 50.0, ("a", "clk_t3"): 100.0})
    _, r = E.eco(b, cur, Site(), M, {"a": "r"}, {"a": "T"}, calib=cal, balance_types=["T"], balance_ps=20.0, k_local=2)
    assert "clk_t3" in [x["port"] for x in r["balanced"]]
    _, r = E.eco(b, cur, Site(), M, {"a": "r"}, {"a": "T"}, calib=cal, balance_types=["T"], balance_ps=20.0, k_local=2, pin=ALL)
    assert r["counts"]["balanced"] == 0


def test_stale_trunk_pin_meta_of_the_base_is_dropped():
    b = base_tree()
    b["meta"] = dict(trunk_pin=dict(waived="old"), trunk_pin_check=dict(checked=3, pruned=0))
    cur = [("a", "clk_t1", 100.0, 50.0), ("a", "clk_t2", 150.0, 0.0), ("a", "clk_t3", 100.0, -50.0)]
    t, _ = E.eco(b, cur, Site(), M, {"a": "r"})
    assert "trunk_pin" not in t["meta"] and "trunk_pin_check" not in t["meta"]
    t, _ = E.eco(b, cur, Site(), M, {"a": "r"}, pin=ALL)
    assert set(t["meta"]["trunk_pin"]["nodes"]) == {"0", "1", "2", "3", "4"}
