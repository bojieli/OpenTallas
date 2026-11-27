"""C-DIECLOCK-TRUNK-UNPINNED die_trial: the post-netlist TRUNK-PIN assert (every pinned node of tree_eco's meta.trunk_pin keeps
xy, parent, level, inv_parity; fix_parity parity nodes are looked through; explicit logged env waiver), physical_pack keeps
pinned homes, and the fine fix_parity grid solves the 450-465 um legs the coarse grid cannot."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clksite_stamp_native as N
import die_trial as D


def nd(i, x, y, parent, level, inv=0, kids=()):
    return dict(id=i, x=x, y=y, parent=parent, level=level, inv_parity=inv, kids=list(kids), taps=[])


def tree():
    # root 0 -> trunk 1 (non-tile) -> 2 (non-tile leaf) and 3 (tile node, not pinned)
    nodes = {0: nd(0, 0.0, 0.0, None, 0, 1, [1]), 1: nd(1, 300.0, 0.0, 0, 1, 0, [2, 3]),
             2: nd(2, 300.0, 200.0, 1, 2, 1), 3: nd(3, 600.0, 0.0, 1, 2, 1)}
    rec = dict(nodes={str(i): [nodes[i]["x"], nodes[i]["y"], nodes[i]["parent"], nodes[i]["level"], nodes[i]["inv_parity"]]
                      for i in (0, 1, 2)}, pruned=[])
    return nodes, rec


def test_unchanged_trunk_passes():
    nodes, rec = tree()
    assert D.trunk_pin_check(nodes, rec) == []
    m = D.enforce_trunk_pin(nodes, rec)
    assert m["violations"] == 0 and m["checked"] == 3


def test_moved_non_tile_node_is_caught(monkeypatch):
    monkeypatch.delenv("OT_TRUNK_PIN_WAIVE", raising=False)
    nodes, rec = tree()
    nodes[2]["x"] += 8.64                       # what physical_pack may do to a trunk cell
    nodes[3]["x"] += 50.0                       # a tile node (not in the record) may move
    bad = D.trunk_pin_check(nodes, rec)
    assert [b["node"] for b in bad] == [2] and "xy" in bad[0]["why"]
    with pytest.raises(ValueError, match=r"TRUNK-PIN.*'node': 2"):
        D.enforce_trunk_pin(nodes, rec)


def test_parent_level_parity_and_missing_are_caught():
    nodes, rec = tree()
    nodes[2].update(parent=0, level=1, inv_parity=0)
    why = D.trunk_pin_check(nodes, rec)[0]["why"]
    assert "parent" in why and "level" in why and "inv_parity" in why
    nodes, rec = tree()
    del nodes[2]
    assert D.trunk_pin_check(nodes, rec) == [dict(node=2, why="missing")]
    rec["pruned"] = [2]
    assert D.trunk_pin_check(nodes, rec) == []


def test_parity_node_on_a_pinned_leg_is_looked_through():
    nodes, rec = tree()
    nodes[9] = nd(9, 300.0, 100.0, 1, 2, 0, [2])          # fix_parity node X between 1 and 2
    nodes[1]["kids"] = [9, 3]
    nodes[2]["parent"] = 9
    assert D.trunk_pin_check(nodes, rec, parity_ids=[9]) == []
    assert D.trunk_pin_check(nodes, rec)[0]["node"] == 2


def test_waiver_is_explicit_and_logged(monkeypatch, capsys):
    nodes, rec = tree()
    nodes[2]["y"] += 1.0
    monkeypatch.setenv("OT_TRUNK_PIN_WAIVE", "probe run, trunk re-form")
    m = D.enforce_trunk_pin(nodes, rec)
    assert m["waived"] == "probe run, trunk re-form" and m["violated_nodes"] == [2]
    assert "TRUNK-PIN WAIVED" in capsys.readouterr().out
    assert D.enforce_trunk_pin(nodes, dict(waived="eco waived"))["waived"] == "eco waived"


class OpenSite:
    def legal(self, q):
        return 0 <= q[0] <= 100 and 0 <= q[1] <= 100


def test_physical_pack_keeps_pinned_homes(monkeypatch):
    monkeypatch.setattr(D, "DME_ACTUAL_MAX_UM", 405.)
    h = (50.004, 50.22)                          # on the body grid (x / 0.054, y / 0.54 integral)
    place = [("a", *h), ("b", *h), ("c", 20.034, 20.0)]
    p0 = {n: (x, y) for n, x, y in D.physical_pack(OpenSite(), place)}
    assert p0["a"] == h and p0["b"] != h        # unpinned: a takes the home first, b is pushed off it
    p = {n: (x, y) for n, x, y in D.physical_pack(OpenSite(), place, pinned={"b"})}
    assert p["b"] == h and p["a"] != h          # pinned b keeps its exact xy; a packs around it
    assert [n for n, *_ in D.physical_pack(OpenSite(), place, pinned={"b"})] == ["a", "b", "c"]
    p = {n: (x, y) for n, x, y in D.physical_pack(OpenSite(), [("b", 50.01, 50.0)], pinned={"b"})}
    assert p["b"] != (50.01, 50.0)              # off the body grid: packs as usual


def leg_nodes(L):
    return {0: dict(id=0, x=0.0, y=0.0, parent=None, kids=[1], level=0, inv_parity=0),
            1: dict(id=1, x=L, y=0.0, parent=0, kids=[], level=1, inv_parity=1)}


def test_fine_parity_grid_solves_a_458um_leg():
    coarse = sorted((0.1 + 0.025 * k for k in range(33)), key=lambda q: abs(q - 0.5))
    n = leg_nodes(458.0)
    assert N.fix_parity(n, 150.0, fractions=coarse)["stats"]["unsolved"] == 1   # the historical grid cannot split it
    n = leg_nodes(458.0)
    assert N.fix_parity(n, 150.0, fractions=N._FINE)["stats"]["unsolved"] == 0  # the fine grid alone does
    n = leg_nodes(458.0)
    r = N.fix_parity(n, 150.0)
    assert r["stats"] == dict(checked=1, inserted=1, unsolved=0)
    X = n[r["ids"][0]]
    assert n[1]["parent"] == X["id"] and X["parent"] == 0
    a = X["x"]
    assert (150.0 <= a < 158.0) or (300.0 <= a < 308.0)


def test_narrow_window_needs_the_analytic_midpoint():
    for L in (450.2, 151.0):          # split windows 0.2 / 1.0 um wide: no grid point falls inside
        assert N.fix_parity(leg_nodes(L), 150.0, fractions=N._COARSE + N._FINE)["stats"]["unsolved"] == 1
        assert N.fix_parity(leg_nodes(L), 150.0)["stats"]["unsolved"] == 0, L


def test_coarse_grid_choice_unchanged_where_it_solves():
    coarse = sorted((0.1 + 0.025 * k for k in range(33)), key=lambda q: abs(q - 0.5))
    assert N.parity_fractions(458.0, 150.0)[:33] == coarse
    for L in (200.0, 520.0, 560.0):
        a, b = leg_nodes(L), leg_nodes(L)
        ra, rb = N.fix_parity(a, 150.0, fractions=coarse), N.fix_parity(b, 150.0)
        assert ra["stats"]["inserted"] == 1 and ra["stats"] == rb["stats"]
        assert {k: (v["x"], v["y"]) for k, v in a.items()} == {k: (v["x"], v["y"]) for k, v in b.items()}


def test_record_shape_is_validated():
    nodes, _ = tree()
    with pytest.raises(ValueError, match="not a tree_eco record"):
        D.trunk_pin_check(nodes, dict(checked=3, pruned=0))


class Site:
    forb = []

    def hits(self, q):
        return []

    def why(self, q):
        return None

    def legal(self, q):
        return -10 <= q[0] <= 1000 and -10 <= q[1] <= 1000

    def nearest(self, q, axis=None):
        return (min(max(q[0], -10), 1000), min(max(q[1], -10), 1000))


def test_end_to_end_eco_tree_through_the_kit_netlist(tmp_path, monkeypatch):
    """tree_eco output -> load_stamped_tree (legalize + fix_parity) -> tree_netlist (inv parity) -> TRUNK-PIN"""
    import json
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "clk"))
    import tree_eco as E
    monkeypatch.delenv("OT_TRUNK_PIN_WAIVE", raising=False)
    site = Site()
    base = {0: nd(0, 0.0, 0.0, None, 0, 0, [1, 3]), 1: nd(1, 300.0, 0.0, 0, 1, 0, [2]), 2: nd(2, 300.0, 200.0, 1, 2),
            3: nd(3, 700.0, 0.0, 0, 1)}
    base[2]["taps"] = [("a", "clk_t1", 300.0, 200.0)]
    base[3]["taps"] = [("b", "clk_t1", 700.0, 0.0)]
    D.tree_netlist(base, [], 150.0, site, clock_cell="inv")          # the base kit's own parity
    T = dict(meta={}, nodes={str(i): {k: v for k, v in n.items() if k != "taps"} for i, n in base.items()},
             taps=[dict(port="t_a__clk_t1", part="a", tap="clk_t1", xy=[300.0, 200.0], node=2),
                   dict(port="t_b__clk_t1", part="b", tap="clk_t1", xy=[700.0, 0.0], node=3)])
    box_b = (650.0, -50.0, 800.0, 50.0)
    pin = E.trunk_pin_set({i: (n["x"], n["y"]) for i, n in base.items()}, site, [box_b])
    assert pin == {0, 1, 2}
    cur = [("a", "clk_t1", 300.0, 200.0), ("b", "clk_t1", 760.0, 30.0)]          # the re-sited type's tap moved
    model = E.Model(None, 150.0)
    t, r = E.eco(T, cur, site, model, {"a": "r", "b": "r"}, {"a": "lep", "b": "tile"}, {"b": box_b},
                 resite_types=["tile"], pin=pin)
    p = tmp_path / "eco.json"
    p.write_text(json.dumps(t))

    def kit(path):
        nodes, taps = D.load_stamped_tree(path, site, 150.0)
        rec = D.STAMPED_INFO["trunk_pin"]
        D.tree_netlist(nodes, taps, 150.0, site, clock_cell="inv", pinned={int(k) for k in rec["nodes"]})
        return D.enforce_trunk_pin(nodes, rec, D.STAMPED_INFO.get("parity_ids", ()))
    assert kit(p)["violations"] == 0
    t["nodes"]["1"]["x"] = 320.0                                                  # a non-tile trunk node moved
    p.write_text(json.dumps(t))
    with pytest.raises(ValueError, match="TRUNK-PIN"):
        kit(p)
