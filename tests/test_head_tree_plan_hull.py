"""HEAD-CORE-LAT-R8: planner rule (COORD RULING HEAD-CORE-LAT-R7 b) -- every non-leaf tree node lies inside the
bounding box of its children, on the face toward its parent when the parent lies beyond it (no leg doubles back),
projected onto legal sites (out of macro halos).  Checks the helper on the elemB R7 N1_1 case and the planner CLI
output (the written spec, parsed independently) on a synthetic clustered core with a macro."""
import importlib.util
import json
import random
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/s81_head/head_tree_plan.py"
spec = importlib.util.spec_from_file_location("head_tree_plan", TOOL)
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)

HALO = 4.33
MAC = (100.0, 150.0, 160.0, 190.0)   # x0 y0 x1 y1


def node(name, xy, kids=()):
    return dict(name=name, xy=xy, kids=list(kids), sinks=[])


def spec_tree(tcl):
    txt = Path(tcl).read_text()
    nodes = {}
    for ln in re.search(r"set ot_ms_tree \{\n(.*?)\n\}", txt, re.S).group(1).splitlines():
        f = ln.strip()[1:-1].split()
        nodes[f[0]] = (f[1], float(f[2]), float(f[3]))
    for ln in re.search(r"set ot_ms_leaves \{\n(.*?)\n\}\nset ot_ms_macros", txt, re.S).group(1).splitlines():
        m = re.match(r"\s*\{(\S+) (\S+) \{(\S+) (\S+)\}", ln)
        nodes[m.group(1)] = (m.group(2), float(m.group(3)), float(m.group(4)))
    r = re.search(r"set ot_ms_root \{(\S+) (\S+)\}", txt).groups()
    nodes["root"] = (None, float(r[0]), float(r[1]))
    return nodes


def violations(nodes, tol=0.01):
    kids = {}
    for n, (p, _, _) in nodes.items():
        if p:
            kids.setdefault(p, []).append(n)
    bad = []
    for n, ks in kids.items():
        if n == "root":
            continue
        for ax in (1, 2):
            lo = min(nodes[k][ax] for k in ks)
            hi = max(nodes[k][ax] for k in ks)
            q, p = nodes[n][ax], nodes[nodes[n][0]][ax]
            if q < lo - tol or q > hi + tol:
                bad.append((n, "box"))
            elif (p > hi + tol and q < hi - tol) or (p < lo - tol and q > lo + tol):
                bad.append((n, "back"))
    return bad


def write_geo(path, seed=7):
    rnd = random.Random(seed)
    lines = ["DIE 0 0 285.12 211.68", "CORE 2.16 2.16 282.96 209.52",
             "MACRO u_rom0 rom %.2f %.2f %.2f %.2f PIN %.2f %.2f" % (MAC + (MAC[0], (MAC[1] + MAC[3]) / 2))]
    k = 0
    for cx, cy, n, s in ((40, 40, 700, 25), (220, 50, 500, 18), (230, 120, 300, 10), (60, 170, 400, 20),
                         (200, 195, 150, 8), (140, 100, 500, 30)):
        while n:
            x, y = rnd.gauss(cx, s), rnd.gauss(cy, s)
            if not (3 < x < 282 and 3 < y < 208) or M.inside((x, y), [dict(rect=MAC)], HALO):
                continue
            lines.append("SINK %.3f %.3f 0 r%d/q CLK" % (x, y, k))
            k += 1
            n -= 1
    Path(path).write_text("\n".join(lines) + "\n")


class HullRule(unittest.TestCase):
    def test_elemB_r7_n1_1_case(self):
        # R7 r7b_f5_24444_b0 sites (CHECKED against p/r7b_f5_24444_b0.tcl): entry (142.56,142.56) -> N1 (210.118,104.5)
        # -> N1_1 (223.548,55.442) -> children up to y 85.064: the U-turn leg
        n11 = node("N1_1", (223.548, 55.442), [node("N1_1_0", (212.703, 29.131)), node("N1_1_1", (237.912, 31.736)),
                                                 node("N1_1_2", (208.097, 85.064)), node("N1_1_3", (237.589, 82.359))])
        n1 = node("N1", (210.118, 104.5), [node("N1_0", (175.138, 67.663)), n11, node("N1_2", (194.693, 144.667)),
                                           node("N1_3", (249.803, 155.658))])
        for k in n11["kids"] + [n1["kids"][i] for i in (0, 2, 3)]:
            k["kids"] = [node(k["name"] + "_0", k["xy"])]   # one leaf below each, at its site
        top = node("", (142.56, 142.56), [n1])
        before = M.hull_violations(top, top["xy"])
        self.assertIn(("N1", "back", "x", 210.12, 175.14, 249.8), before)
        M.apply_hull(top, top["xy"], [], HALO)
        self.assertEqual(M.hull_violations(top, top["xy"]), [])
        self.assertEqual(tuple(round(c, 3) for c in n1["xy"]), (175.138, 104.5))   # W face toward the entry; y in span
        self.assertEqual(tuple(round(c, 3) for c in n11["xy"]), (208.097, 85.064))  # N1_1 on its NW face: no U-turn
        # every root->leaf path below N1 is now monotone in y (no leg goes S then back N)
        for k in n11["kids"]:
            self.assertLessEqual(abs(n1["xy"][1] - n11["xy"][1]) + abs(n11["xy"][1] - k["xy"][1]),
                                 abs(n1["xy"][1] - k["xy"][1]) + 1e-6)

    def test_box_and_legal_projection(self):
        mac = [dict(rect=MAC)]
        b = ((90.0, 170.0), (160.0, 160.0))      # pinned y inside the macro, x span crosses it
        q = M.hull_site((130.0, 160.0), b, mac, HALO)
        self.assertFalse(M.inside(q, mac, HALO))
        self.assertTrue(90.0 <= q[0] <= 170.0 and q[1] == 160.0)
        with self.assertRaises(SystemExit):
            M.hull_site((130.0, 160.0), ((120.0, 140.0), (160.0, 170.0)), mac, HALO)

    def test_cli_spec_obeys_rule(self):
        with tempfile.TemporaryDirectory() as d:
            geo = Path(d) / "t.geo"
            write_geo(geo)
            res = {}
            for h in (0, 1):
                out = Path(d) / f"p{h}"
                r = subprocess.run([sys.executable, "-I", str(TOOL), str(geo), str(out), "--fanouts", "2,4,4,4",
                                    "--entry", "142.56,106", "--seg", "1000", "--fringe", "8,1,6", "--hull", str(h)],
                                   capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
                nodes = spec_tree(str(out) + ".tcl")
                pj = json.loads((Path(str(out) + ".plan.json")).read_text())
                res[h] = (violations(nodes), pj["hull"], nodes)
            self.assertGreater(len(res[0][0]), 0, "legacy siting should show the doubled-back legs")
            self.assertEqual(res[0][1]["after"], len(res[0][0]))
            self.assertEqual(res[1][0], [])
            self.assertEqual(res[1][1]["after"], 0)
            for n, (p, x, y) in res[1][2].items():
                if p:
                    self.assertFalse(M.inside((x, y), [dict(rect=MAC)], HALO - 0.01), n)
            leaves0 = {n for n in res[0][2] if n.count("_") == 3}
            leaves1 = {n for n in res[1][2] if n.count("_") == 3}
            self.assertEqual(leaves0, leaves1)
            for n in leaves1:                                    # leaves stay at their sink centroids
                self.assertEqual(res[0][2][n][1:], res[1][2][n][1:])


if __name__ == "__main__":
    unittest.main()
