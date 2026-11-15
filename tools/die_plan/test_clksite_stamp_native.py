import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import clksite_stamp as K
import clksite_stamp_native as N

W, H = 100.0, 100.0


class FakeP:
    """two tiles of one type: A at (0,0) R0, B at (200,0) MY"""
    types = {"t": {"outline_um": [W, H]}}
    parts = {"A": {"type": "t", "origin_um": [0.0, 0.0]}, "B": {"type": "t", "origin_um": [200.0, 0.0]}}
    _o = {"A": "R0", "B": "MY"}

    def rect(self, n):
        o = self.parts[n]["origin_um"]
        return (o[0], o[1], o[0] + W, o[1] + H)

    def orient(self, n): return self._o[n]

    def to_type(self, n, pt):
        o = self.parts[n]["origin_um"]
        x, y = pt[0] - o[0], pt[1] - o[1]
        return {"R0": (x, y), "MY": (W - x, y)}[self._o[n]]


def node(i, x, y, parent, kids):
    return dict(id=i, x=x, y=y, parent=parent, kids=kids, level=0, inv_parity=0, ntaps=0)


def tree():
    # root 0 outside both tiles; tile A: 1 (top) -> 2, 3 ; tile B: 4 (top, other position) -> 5, 6
    n = {0: node(0, -50.0, 50.0, None, [1, 4]),
         1: node(1, 10.0, 20.0, 0, [2, 3]), 2: node(2, 60.0, 20.0, 1, []), 3: node(3, 10.0, 70.0, 1, []),
         4: node(4, 280.0, 50.0, 0, [5, 6]), 5: node(5, 230.0, 50.0, 4, []), 6: node(6, 250.0, 90.0, 4, [])}
    taps = [dict(port="t_A__clk_t0", part="A", tap="clk_t0", xy=[60.0, 20.0], node=2),
            dict(port="t_A__clk_t1", part="A", tap="clk_t1", xy=[10.0, 70.0], node=3),
            dict(port="t_B__clk_t0", part="B", tap="clk_t0", xy=[230.0, 50.0], node=5),
            dict(port="t_B__clk_t1", part="B", tap="clk_t1", xy=[250.0, 90.0], node=6)]
    return dict(meta={}, nodes={str(k): v for k, v in n.items()}, taps=taps,
                node_buf={str(k): f"b{k}" for k in n}, parent_of={f"b{k}": f"b{v['parent']}" for k, v in n.items() if v["parent"] is not None},
                sites={f"b{k}": [v["x"], v["y"]] for k, v in n.items()})


class T(unittest.TestCase):
    def setUp(self):
        self.out, self.rep = N.stamp_tree(FakeP(), tree(), "t", max_slide=0.0)
        self.nodes = {int(k): v for k, v in self.out["nodes"].items()}

    def test_counts_and_consistency(self):
        self.assertEqual(self.rep["stamped"], 2)
        # 7 nodes + one parity node per re-laid boundary leg whose kit-laid inverter count has the wrong parity
        self.assertEqual(len(self.nodes), 7 + self.rep["parity_nodes"]["inserted"])
        self.assertEqual(self.rep["parity_nodes"]["unsolved"], 0)
        self.assertEqual(len(self.out["taps"]), 4)
        for i, v in self.nodes.items():
            if v["parent"] is not None:
                self.assertIn(i, self.nodes[v["parent"]]["kids"])
            for k in v["kids"]:
                self.assertEqual(self.nodes[k]["parent"], i)

    def test_mirrored_instance_sits_on_the_template_sites(self):
        # both tiles: the type-frame lower-left of every stamped node is identical (the same sites in every instance)
        P = FakeP()
        sets = {}
        for v in self.nodes.values():
            for n in ("A", "B"):
                r = P.rect(n)
                if r[0] <= v["x"] < r[2]:
                    box = K.cell_box((v["x"] - K.HALO[0] + 1.35, v["y"] - K.HALO[1] + 0.405))      # die box from the site
                    ob = K.orient_rect((box[0] - P.parts[n]["origin_um"][0], box[1], box[2] - P.parts[n]["origin_um"][0], box[3]),
                                       (W, H), P.orient(n))
                    sets.setdefault(n, set()).add((round(ob[0], 3), round(ob[1], 3)))
        self.assertEqual(sets["A"], sets["B"])

    def test_parity_of_every_stamped_leg_matches(self):
        import math
        for i, v in self.nodes.items():
            if v.get("stamp_leg") and v["parent"] in self.nodes:
                p = self.nodes[v["parent"]]
                nrep = max(0, math.ceil((abs(p["x"] - v["x"]) + abs(p["y"] - v["y"])) / 150.0) - 1)
                self.assertEqual((nrep + 1) & 1, (v["inv_parity"] ^ p["inv_parity"]) & 1, (i, nrep))

    def test_class_by_counts_merges_classes(self):
        out, rep = N.stamp_tree(FakeP(), tree(), "t", max_slide=0.0, class_by="counts")
        self.assertEqual(rep["stamped"], 2)
        self.assertEqual(len(rep["classes"]), 1)
        self.assertEqual(len(out["taps"]), 4)

    def test_taps_follow_by_name_and_top_priced(self):
        by = {(t["part"], t["tap"]): t for t in self.out["taps"]}
        self.assertEqual(set(by), {("A", "clk_t0"), ("A", "clk_t1"), ("B", "clk_t0"), ("B", "clk_t1")})
        tops = [v for v in self.nodes.values() if v["parent"] == 0]
        self.assertEqual(len(tops), 2)
        for v in tops:
            self.assertIn("stamp_leg", v)
            self.assertNotIn("physical_leg", v)
        self.assertEqual(self.rep["legs_over_405"], 0)


if __name__ == "__main__":
    unittest.main()
