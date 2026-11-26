"""CLK-ECO-1 tree_eco: site match is name-agnostic, unmoved leaves keep node/site/chain, moved taps reuse freed leaves,
new taps hang on the best internal node, stranded leaves re-site to their tap, lifts keep Manhattan lengths."""
import tree_eco as E


class Site:
    """legal everywhere except y in (forb_lo, forb_hi)"""
    def __init__(self, forb=None):
        self.forb = forb

    def legal(self, q):
        return not (self.forb and self.forb[0] < q[1] < self.forb[1])

    def nearest(self, q):
        if self.legal(q):
            return q
        lo, hi = self.forb
        return (q[0], lo if q[1] - lo < hi - q[1] else hi)


def leg(n, d=10.0):
    return dict(chain=[[0, 0], [0, 0]], stages=1, delay_ps=d, wire_um=0.0)


def base_tree():
    # root 0 -> merge 1 (region r) -> leaves 2,3,4 at the taps
    N = {
        "0": dict(id=0, x=0.0, y=0.0, parent=None, level=0, kids=[1], inv_parity=0, region_root="r"),
        "1": dict(id=1, x=100.0, y=0.0, parent=0, level=1, kids=[2, 3, 4], inv_parity=1, dme="r", physical_leg=leg(1, 30.0)),
        "2": dict(id=2, x=100.0, y=50.0, parent=1, level=2, kids=[], inv_parity=0, dme="r", physical_leg=leg(2, 20.0)),
        "3": dict(id=3, x=150.0, y=0.0, parent=1, level=2, kids=[], inv_parity=0, dme="r", physical_leg=leg(3, 20.0)),
        "4": dict(id=4, x=100.0, y=-50.0, parent=1, level=2, kids=[], inv_parity=0, dme="r", physical_leg=leg(4, 20.0)),
    }
    T = [dict(port="t_a__clk_t1", part="a", tap="clk_t1", xy=[100.0, 50.0], node=2),
         dict(port="t_a__clk_t2", part="a", tap="clk_t2", xy=[150.0, 0.0], node=3),
         dict(port="t_a__clk_t3", part="a", tap="clk_t3", xy=[100.0, -50.0], node=4)]
    return dict(meta={}, nodes=N, taps=T)


M = E.Model(dict(leg=[8.8, 0.24, 0.0, 10.0], tap=[0.15, 0.0]), 150.0)


def test_renumbered_taps_match_by_site_and_keep_chains():
    b = base_tree()
    cur = [("a", "clk_t3", 100.0, 50.0), ("a", "clk_t1", 150.0, 0.0), ("a", "clk_t2", 100.0, -50.0)]   # names rotated
    t, r = E.eco(b, cur, Site(), M, {"a": "r"})
    assert r["counts"]["matched"] == 3 and r["counts"]["unmatched"] == 0 and r["counts"]["relaid_legs"] == 0
    by = {x["tap"]: x["node"] for x in t["taps"]}
    assert by == {"clk_t3": 2, "clk_t1": 3, "clk_t2": 4}
    for i in ("1", "2", "3", "4"):
        assert t["nodes"][i]["physical_leg"] == b["nodes"][i]["physical_leg"]


def test_moved_tap_reuses_freed_leaf_no_new_node():
    b = base_tree()
    cur = [("a", "clk_t1", 100.0, 50.0), ("a", "clk_t2", 160.0, 0.0), ("a", "clk_t3", 100.0, -50.0)]
    t, r = E.eco(b, cur, Site(), M, {"a": "r"})
    assert r["counts"]["attached"] == {"moved": {"reuse": 1}}
    assert len(t["nodes"]) == 5
    n3 = t["nodes"]["3"]
    assert (n3["x"], n3["y"]) == (160.0, 0.0) and "physical_leg" not in n3
    assert t["nodes"]["2"]["physical_leg"] == b["nodes"]["2"]["physical_leg"]      # unmoved leaf untouched


def test_new_tap_hangs_and_gone_leaf_pruned():
    b = base_tree()
    cur = [("a", "clk_t1", 100.0, 50.0), ("a", "clk_t2", 150.0, 0.0), ("a", "clk_t3", 100.0, -50.0),
           ("a", "clk_t4", 60.0, 0.0)]
    t, r = E.eco(b, cur, Site(), M, {"a": "r"})
    a = r["attached"][0]
    assert a["kind"] == "new" and a["how"] == "hang" and a["parent"] in (0, 1)
    assert r["counts"]["unplaced"] == 0
    cur2 = [("a", "clk_t1", 100.0, 50.0), ("a", "clk_t2", 150.0, 0.0)]
    t2, r2 = E.eco(b, cur2, Site(), M, {"a": "r"})
    assert r2["counts"]["gone"] == 1 and r2["counts"]["pruned"] == 1 and "4" not in t2["nodes"]
    assert 4 not in t2["nodes"]["1"]["kids"]


def test_stranded_leaf_resites_to_tap_once_legal():
    b = base_tree()
    b["taps"][0]["xy"] = [100.0, 90.0]              # leaf 2 sits 40 um below its tap (old keep-out edge)
    cur = [("a", "clk_t1", 100.0, 90.0), ("a", "clk_t2", 150.0, 0.0), ("a", "clk_t3", 100.0, -50.0)]
    t, r = E.eco(b, cur, Site((60.0, 100.0)), M, {"a": "r"})       # still forbidden: stays near the edge
    assert r["counts"]["resited_leaves"] == 1 and t["nodes"]["2"]["y"] in (50.0, 60.0, 100.0)
    t, r = E.eco(b, cur, Site(), M, {"a": "r"})                     # floor lifted: leaf goes onto the tap
    assert (t["nodes"]["2"]["x"], t["nodes"]["2"]["y"]) == (100.0, 90.0)
    assert r["resite"][0]["leg_was_um"] == 40.0


def test_lift_preserves_manhattan_lengths():
    b = base_tree()
    # merge 1 at y 0, kids all above: lift moves it up, root->kid lengths unchanged
    b["nodes"]["2"].update(x=100.0, y=80.0); b["nodes"]["3"].update(x=140.0, y=60.0); b["nodes"]["4"].update(x=60.0, y=70.0)
    b["taps"][0]["xy"] = [100.0, 80.0]; b["taps"][1]["xy"] = [140.0, 60.0]; b["taps"][2]["xy"] = [60.0, 70.0]
    cur = [("a", "clk_t1", 100.0, 80.0), ("a", "clk_t2", 140.0, 60.0), ("a", "clk_t3", 60.0, 70.0)]
    L0 = {k: E.man((0, 0), (100, 0)) + E.man((100, 0), xy) for k, xy in (("2", (100, 80)), ("3", (140, 60)), ("4", (60, 70)))}
    t, r = E.eco(b, cur, Site(), M, {"a": "r"}, {"a": "T"}, {"a": (0, -100, 300, 300)}, resite_types=["T"], lift_tol_ps=50.0)
    assert r["counts"]["lifted"] >= 1
    n1 = t["nodes"]["1"]
    for k in ("2", "3", "4"):
        kv = t["nodes"][k]
        assert abs(E.man((0, 0), (n1["x"], n1["y"])) + E.man((n1["x"], n1["y"]), (kv["x"], kv["y"])) - L0[k]) < 1e-6
    assert n1["y"] > 0


def test_parity_follows_relaid_legs_only():
    b = base_tree()
    cur = [("a", "clk_t1", 100.0, 50.0), ("a", "clk_t2", 460.0, 0.0), ("a", "clk_t3", 100.0, -50.0)]
    t, r = E.eco(b, cur, Site(), M, {"a": "r"})
    n1, n3 = t["nodes"]["1"], t["nodes"]["3"]
    # leg 1->3 is 360 um: 3 stages -> parity flips relative to the parent
    assert n3["inv_parity"] == n1["inv_parity"] ^ 1
    assert t["nodes"]["2"]["inv_parity"] == b["nodes"]["2"]["inv_parity"]


def test_split_part_inherits_leaves_at_its_sites():
    b = base_tree()
    cur = [("a", "clk_t1", 100.0, 50.0), ("a_w", "clk_t1", 150.0, 0.0), ("a", "clk_t3", 100.0, -50.0)]
    t, r = E.eco(b, cur, Site(), M, {"a": "r", "a_w": "r"})
    assert r["counts"]["matched"] == 3 and r["counts"]["gone"] == 0
    assert {x["port"]: x["node"] for x in t["taps"]}["t_a_w__clk_t1"] == 3


def test_local_target_follows_neighbourhood():
    b = base_tree()
    b["nodes"]["2"]["physical_leg"]["delay_ps"] = 60.0      # tap 1 late, taps 2/3 on time
    cur = [("a", "clk_t1", 100.0, 50.0), ("a", "clk_t2", 150.0, 0.0), ("a", "clk_t3", 100.0, -50.0),
           ("a", "clk_t9", 101.0, 52.0)]
    _, rl = E.eco(b, cur, Site(), M, {"a": "r"}, k_local=1)
    _, rp = E.eco(b, cur, Site(), M, {"a": "r"}, target="part")
    assert rl["attached"][0]["target_ps"] == 90.0 and rp["attached"][0]["target_ps"] == 50.0


def test_new_core_tap_targets_planned_early():
    b = base_tree()
    cur = [("a", "clk_t1", 100.0, 50.0), ("a", "clk_t2", 150.0, 0.0), ("a", "clk_t3", 100.0, -50.0),
           ("a", "clk_c0", 90.0, 0.0)]
    _, r = E.eco(b, cur, Site(), M, {"a": "r"}, early={("a", "clk_c0"): 20.0})
    assert r["attached"][0]["target_ps"] == 30.0          # glue 50 - early 20


def test_calib_attaches_on_routed_parent_arrivals():
    b = base_tree()
    # a 2nd internal node 5 hangs off the root; the model prices it equal to node 1 (and cheaper: fewer taps under it),
    # routed says node 1 is 40 ps later
    b["nodes"]["5"] = dict(id=5, x=100.0, y=10.0, parent=0, level=1, kids=[6], inv_parity=1, dme="r", physical_leg=leg(5, 30.0))
    b["nodes"]["6"] = dict(id=6, x=100.0, y=20.0, parent=5, level=2, kids=[], inv_parity=0, dme="r", physical_leg=leg(6, 20.0))
    b["nodes"]["0"]["kids"] = [1, 5]
    b["taps"].append(dict(port="t_a__clk_t4", part="a", tap="clk_t4", xy=[100.0, 20.0], node=6))
    cur = [("a", "clk_t1", 100.0, 50.0), ("a", "clk_t2", 150.0, 0.0), ("a", "clk_t3", 100.0, -50.0),
           ("a", "clk_t4", 100.0, 20.0), ("a", "clk_t9", 105.0, 5.0)]
    cal = dict(node={0: 0.0, 1: 70.0, 5: 30.0}, leg=(0.0, 1.0),
               tap={("a", "clk_t1"): 90.0, ("a", "clk_t2"): 90.0, ("a", "clk_t3"): 90.0, ("a", "clk_t4"): 50.0})
    _, r = E.eco(b, cur, Site(), M, {"a": "r"}, calib=cal, k_local=4)
    a = r["attached"][0]
    assert a["target_ps"] == 90.0 and a["parent"] == 1          # node 1 (routed 70) reaches 90, node 5 (routed 30) falls short
    assert r["calib"]["nodes"] == 3
    _, r0 = E.eco(b, cur, Site(), M, {"a": "r"}, k_local=4)
    assert r0["attached"][0]["parent"] == 5                    # model-only: the cheaper fanout wins


def test_balance_detaches_routed_outlier_only():
    b = base_tree()
    for i, (x, y) in ((5, (60.0, 0.0)), (6, (100.0, 0.0))):
        b["nodes"][str(i)] = dict(id=i, x=x, y=y, parent=1, level=2, kids=[], inv_parity=0, dme="r", physical_leg=leg(i, 20.0))
        b["nodes"]["1"]["kids"].append(i)
        b["taps"].append(dict(port=f"t_a__clk_t{i - 1}", part="a", tap=f"clk_t{i - 1}", xy=[x, y], node=i))
    cur = [("a", "clk_t1", 100.0, 50.0), ("a", "clk_t2", 150.0, 0.0), ("a", "clk_t3", 100.0, -50.0),
           ("a", "clk_t4", 60.0, 0.0), ("a", "clk_t5", 100.0, 0.0)]
    cal = dict(node={0: 0.0, 1: 30.0}, leg=(0.0, 1.0),
               tap={("a", "clk_t1"): 50.0, ("a", "clk_t2"): 50.0, ("a", "clk_t3"): 100.0, ("a", "clk_t4"): 50.0,
                    ("a", "clk_t5"): 52.0})
    _, r = E.eco(b, cur, Site(), M, {"a": "r"}, {"a": "T"}, calib=cal, balance_types=["T"], balance_ps=20.0)
    assert [x["port"] for x in r["balanced"]] == ["clk_t3"] and r["counts"]["balanced"] == 1
    assert r["attached"][0]["port"] == "clk_t3" and r["attached"][0]["kind"] == "balance"
    _, r0 = E.eco(b, cur, Site(), M, {"a": "r"}, {"a": "T"}, calib=cal)
    assert r0["counts"]["balanced"] == 0 and r0["counts"]["matched"] == 5


def test_max_attach_leg_caps_reuse_and_hang():
    b = base_tree()
    cur = [("a", "clk_t1", 100.0, 50.0), ("a", "clk_t2", 400.0, 0.0), ("a", "clk_t3", 100.0, -50.0)]
    _, r = E.eco(b, cur, Site(), M, {"a": "r"})
    assert r["attached"][0]["how"] == "reuse"              # 300 um re-laid leg from node 1
    _, r = E.eco(b, cur, Site(), M, {"a": "r"}, max_attach_leg_um=100.0)
    assert r["counts"]["unplaced"] == 0                     # nothing within 100 um: soft cap falls back to the long leg
    cur2 = cur + [("a", "clk_t9", 160.0, 20.0)]
    _, r2 = E.eco(b, cur2, Site(), M, {"a": "r"}, max_attach_leg_um=100.0)
    a9 = [x for x in r2["attached"] if x["port"] == "clk_t9"][0]
    assert a9["parent"] == 1 or a9["how"] == "hang"          # a short option exists: the 300 um reuse is not taken for it
