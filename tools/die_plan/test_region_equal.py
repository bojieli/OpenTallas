"""LAND-S81-1: --region-equal pads region roots so every region's modelled slowest entry matches within one stage."""
import die_trial as DT


def _tree():
    # root -> A (near, shallow region "small") and B (far, deep region "big")
    n = {}

    def mk(i, x, y, parent, region_root=None, taps=()):
        n[i] = dict(id=i, x=x, y=y, parent=parent, level=0, kids=[], taps=list(taps))
        if region_root:
            n[i]["region_root"] = region_root
        if parent is not None:
            n[parent]["kids"].append(i)
    mk(0, 0.0, 0.0, None)
    mk(1, 100.0, 0.0, 0, "small", [("pa", "clk", 120.0, 0.0)])
    mk(2, 2000.0, 0.0, 0, "big")
    mk(3, 3000.0, 0.0, 2, None, [("pb", "clk", 3000.0, 50.0)])
    mk(4, 4000.0, 0.0, 3, None, [("pc", "clk", 4000.0, 10.0)])
    return n


def test_pads_small_region_only():
    n = _tree()
    m = DT.region_equalise(n, 450.0)
    assert m["regions"] == 2
    assert n[2]["pad"] == 0
    assert n[1]["pad"] > 0
    assert m["spread_after_ps"] <= DT.EQ_STAGE_TT[0] / 2 + 1e-6
    assert m["spread_before_ps"] > m["spread_after_ps"]


def test_netlist_emits_pad_chain():
    n = _tree()
    DT.region_equalise(n, 450.0)
    taps = [t for nd in n.values() for t in nd["taps"]]
    v, place, *_ = DT.tree_netlist(n, taps, 450.0)
    k = n[1]["pad"]
    assert sum(1 for inst, *_ in place if inst.startswith("q1_")) == k
    assert f"q1_{k - 1}" in v and ".A(qn1_" in v
