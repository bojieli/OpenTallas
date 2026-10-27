"""HEAD-CORE-R17: symmetric equal-leg die tree (head_mesh_r3 --symmetric), M8 densify, LEF pin files."""
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "die_plan"))
import head_mesh_r3 as H  # noqa: E402
import head_pins_from_lef as PF  # noqa: E402


class ET:
    reach = 450.0

    def nseg(self, L):
        import math
        return max(1, math.ceil(L / self.reach - 1e-9))

    def delay(self, L, c, n=None):
        return (n or self.nseg(L)) * (30.0 + 0.1 * L / (n or self.nseg(L)))


def _tree(drv, st_rows=()):
    nodes, top, info, moves = H.build_tree_sym(drv, list(st_rows), ET(), (500.0, 520.0), 500.0, 2)
    by = {n["tag"]: n for n in nodes}
    return nodes, top, info, moves, by


def _depth(n, by):
    k = 0
    while n.get("parent"):
        n = by[n["parent"]]
        k += 1
    return k


def test_equal_legs_per_level_and_equal_depth():
    xs = [100.0 + 50 * i for i in range(7)] + [900.0 - 50 * i for i in range(7)]   # mirrored about 500, odd count
    ys = [200.0 + 100 * j for j in range(6)]
    drv = [(x, y) for x in xs for y in ys]
    nodes, top, info, moves, by = _tree(drv)
    lv = defaultdict(set)
    for n in nodes:
        if n.get("parent"):
            lv[_depth(n, by)].add(round(n["leg"], 6))
    assert all(len(v) == 1 for v in lv.values()), lv            # one leg length per level: equal by construction
    leaves = [n for n in nodes if not n["kids"]]
    assert len(leaves) == len(drv) and len({_depth(n, by) for n in leaves}) == 1
    assert sorted((round(n["xy"][0], 3), round(n["xy"][1], 3)) for n in leaves) == sorted(drv)


def test_sizing_single_child_half_drive():
    xs = [100.0, 150.0, 200.0, 800.0, 850.0, 900.0]                # 3 per side: lattice of 4, one slot pruned
    nodes, top, info, moves, by = _tree([(x, 300.0) for x in xs] + [(x, 400.0) for x in xs])
    one = [n for n in nodes if n["kids"] and len(n["kids"]) == 1 and n["tag"] != "SRC"]
    two = [n for n in nodes if n["kids"] and len(n["kids"]) == 2]
    assert one and two
    assert all(n["drive_mult"] == 2 for n in one) and all(n["drive_mult"] == 4 for n in two)


def test_station_row_moves_to_free_slot():
    xs = [250.0, 300.0, 700.0, 750.0]
    drv = [(x, 200.0 + 100 * j) for x in xs for j in range(4)] + [(x, 40.0) for x in xs]
    nodes, top, info, moves, by = _tree(drv, st_rows=[40.0])
    assert moves == {40.0: 0.0}                                    # nearest free half-integer slot (yc 350, pitch 100: 0 / 100)
    lv = defaultdict(set)
    for n in nodes:
        if n.get("parent"):
            lv[_depth(n, by)].add(round(n["leg"], 6))
    assert all(len(v) == 1 for v in lv.values())


def test_off_lattice_refused():
    xs = [100.0, 150.0, 210.0, 790.0, 850.0, 900.0]
    try:
        _tree([(x, 300.0) for x in xs] + [(x, 400.0) for x in xs])
    except SystemExit:
        return
    raise AssertionError("off-lattice column accepted")


def test_densify_m8_max_gap():
    S = [("M8", y, 0.0, 10.0, "tile_row") for y in (0.0, 185.76, 371.52, 708.48)] + [("M9", 5.0, 0.0, 708.48, "column_full")]
    out = H.densify_m8(S, 144.0)
    ys = sorted(f for L, f, *_ in out if L == "M8")
    assert max(b - a for a, b in zip(ys, ys[1:])) <= 144.0 + 1e-6
    assert len(ys) == 4 + 1 + 1 + 2


def test_pins_from_lef(tmp_path):
    lef = tmp_path / "c.lef"
    lef.write_text("MACRO m\n  SIZE 10 BY 20 ;\n  PIN ft_mstrap_i\n    PORT\n      LAYER M5 ;\n        RECT 4.904 9.904 5.096 10.096 ;\n"
                   "    END\n  END ft_mstrap_i\n  PIN a\n    PORT\n      LAYER M4 ;\n        RECT 0 1 0.1 1.2 ;\n    END\n  END a\nEND m\n")
    out = tmp_path / "p.json"
    PF.main([str(lef), str(out), "--source-label", "x"])
    d = json.loads(out.read_text())
    assert d["outline_um"] == [10.0, 20.0]
    pin = {p["name"]: p for p in d["pins"]}["ft_mstrap_i"]
    assert (pin["x"], pin["y"], pin["layer"]) == (5.0, 10.0, "M5")
    d2 = dict(d, source="other")
    assert PF.canon_sha(d2["pins"], d2["outline_um"]) == d["pins_canon_sha256"]
