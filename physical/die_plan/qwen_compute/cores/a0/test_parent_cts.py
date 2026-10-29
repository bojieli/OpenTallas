#!/usr/bin/env python3
"""QC-A0-KITS-10: A0 parent kit CTS hook, python side (parent_cts.py) + its hand-off to the shared planner
tools/die_plan/parent_trunk_dme.py plan --ungated-split / tcl.
    python3 -m unittest physical/die_plan/qwen_compute/cores/a0/test_parent_cts.py"""
import json
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import parent_cts as PC  # noqa: E402

DME = HERE.parents[4] / "tools/die_plan/parent_trunk_dme.py"


def synth_sinks(path, seed=7):
    """400x600 um parent, two child macros (W column), 900 gated regs spread E, 120 ungated face regs on the E edge"""
    rnd = random.Random(seed); u = 1000
    L = ["DIE 0 0 %d %d %d" % (400 * u, 600 * u, u),
         "MACRO u_k0 ot_qwen_tile_node %d %d %d %d" % (10 * u, 50 * u, 60 * u, 250 * u),
         "MACRO u_k1 ot_qwen_tile_node %d %d %d %d" % (10 * u, 330 * u, 60 * u, 530 * u),
         "SINK u_k0 ot_qwen_tile_node clk %d %d 0 1" % (35 * u, 150 * u),
         "SINK u_k1 ot_qwen_tile_node clk %d %d 0 1" % (35 * u, 430 * u)]
    for i in range(900):
        L.append("SINK u_g.r\\[%d\\] DFFHQNx1_ASAP7_75t_R CLK %d %d 0 0" % (i, rnd.uniform(80, 390) * u, rnd.uniform(10, 590) * u))
    for i in range(120):
        L.append("SINK u_g.n_a_q\\[%d\\] DFFHQNx1_ASAP7_75t_R CLK %d %d 1 0" % (i, rnd.uniform(370, 392) * u, rnd.uniform(100, 500) * u))
    Path(path).write_text("\n".join(L) + "\n")


class Cluster(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); self.d = Path(self.t.name)
        synth_sinks(self.d / "s.txt")

    def tearDown(self):
        self.t.cleanup()

    def test_never_mixed_box_and_legal_roots(self):
        G = PC.cluster(self.d / "s.txt")
        self.assertEqual(sum(c["n"] for c in G["clusters"]), 1020)
        ung = [c for c in G["clusters"] if c.get("ungated")]
        self.assertTrue(ung)
        self.assertEqual(sum(c["n"] for c in ung), 120)
        self.assertTrue(all(all("n_a_q" in r for r in c["regs"]) for c in ung))
        self.assertTrue(all(not any("n_a_q" in r for r in c["regs"]) for c in G["clusters"] if not c.get("ungated")))
        for c in G["clusters"]:
            b = c["box"]
            self.assertLessEqual(max(b[2] - b[0], b[3] - b[1]), 200.0 + 1e-6)
            x, y = c["root"]
            self.assertFalse(any(m[0] - 1 < x < m[2] + 1 and m[1] - 1 < y < m[3] + 1 for m in G["macros"]))
        self.assertEqual([k["inst"] for k in G["kids"]], ["u_k0", "u_k1"])
        self.assertIn("lappend PT_CL [list", PC.cl_tcl(G))
        self.assertEqual(G, PC.cluster(self.d / "s.txt"))          # deterministic

    def test_cli_refuses_without_ungated(self):
        t = (self.d / "s.txt").read_text().replace(" 1 0\n", " 0 0\n")
        (self.d / "g.txt").write_text(t)
        r = subprocess.run([sys.executable, str(HERE / "parent_cts.py"), "cluster", str(self.d / "g.txt"),
                            str(self.d / "c.json"), str(self.d / "c.tcl")], capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no ungated", r.stderr)

    def test_clins_and_planner_handoff(self):
        G = PC.cluster(self.d / "s.txt")
        cj = self.d / "cl.json"; cj.write_text(json.dumps(G))
        arr = []
        for c in G["clusters"]:
            arr.append("T %s_root/A 100.0 80.0" % c["name"])
            for k, r in enumerate(c["regs"]):
                arr.append("S %s/CLK %s %.1f %.1f" % (r, c["name"], 160.0 + k % 5, 130.0 + k % 3))
        (self.d / "arr.txt").write_text("\n".join(arr) + "\n")
        ins = PC.clins(self.d / "arr.txt", G)
        self.assertEqual(set(ins), {c["name"] for c in G["clusters"]})
        c0 = G["clusters"][0]["name"]
        self.assertGreaterEqual(ins[c0]["TT"]["mean"], 60.0); self.assertLessEqual(ins[c0]["TT"]["max"], 64.0)
        self.assertGreaterEqual(ins[c0]["FF"]["min"], 50.0)
        # a missing register arrival fails closed
        (self.d / "bad.txt").write_text("\n".join(arr[:-1]) + "\n")
        with self.assertRaises(ValueError):
            PC.clins(self.d / "bad.txt", G)
        ij = self.d / "clins.json"; ij.write_text(json.dumps(ins))
        r = subprocess.run([sys.executable, str(DME), "plan", str(cj), str(ij), str(self.d / "tr.json"),
                            "--entry", "200,300", "--ungated-split", "--topology", "bipart"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        tr = json.loads((self.d / "tr.json").read_text())
        self.assertEqual(sorted(tr["summary"]["ungated_split"]["ungated_sinks"]),
                         sorted(c["name"] for c in G["clusters"] if c.get("ungated")))
        r = subprocess.run([sys.executable, str(DME), "tcl", str(self.d / "tr.json"), str(self.d / "tr.tcl")],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        t = (self.d / "tr.tcl").read_text()
        self.assertIn("set ROOT_NET", t); self.assertIn("set ICG_IN", t)


if __name__ == "__main__":
    unittest.main()
