import unittest
import kit_fit as KF


def core(inst, x, y, w, h, off=(0.0, 0.0)):
    return {"inst": inst, "lef": "x.lef", "origin_um": [x, y], "outline_um": [w, h], "track_offset_um": list(off)}


class Fit(unittest.TestCase):
    def test_f2s3_halves_abut_in_the_plan_but_overlap_at_kit_offsets(self):
        # origins abut (10.0 + 20 = 30.0), offsets 0.108 / 0.684 put the left half's east edge 0.576 past the right half's west edge
        t = {"outline_um": [100, 100], "hard_cores": [core("u_w", 10, 10, 20, 20, (0.684, 0.0)), core("u_e", 30, 10, 20, 20, (0.108, 0.0))]}
        f = KF.findings({"t": t})
        self.assertEqual(len(f), 1, f)
        self.assertIn("KITFIT-OVERLAP type t: u_w / u_e overlap 0.576 x 20", f[0])

    def test_same_offsets_stay_abutted(self):
        t = {"outline_um": [100, 100], "hard_cores": [core("a", 10, 10, 20, 20, (0.108, 0.012)), core("b", 30, 10, 20, 20, (0.108, 0.012))]}
        self.assertEqual(KF.findings({"t": t}), [])

    def test_halo(self):
        t = {"outline_um": [60, 40], "macro_halo_um": 1.0, "hard_cores": [core("a", 0, 0, 20, 20), core("b", 20.5, 0, 20, 20), core("c", 50, 0, 20, 20)]}
        f = KF.findings({"t": t})
        self.assertEqual(len(f), 1, f)
        self.assertTrue(f[0].startswith("KITFIT-HALO") and "a / b" in f[0] and "0.5" in f[0], f)
        self.assertEqual(KF.findings({"t": dict(t, macro_halo_um=0)}), [])

    def test_contents_and_hard_cores_and_message_cap(self):
        t = {"outline_um": [1000, 1000], "hard_cores": [core("h", 0, 0, 10, 10)],
             "contents": [{"inst": "s", "lef": "s.lef", "origin_um": [5, 5], "outline_um": [10, 10]}, {"inst": "nolef", "origin_um": [0, 0], "outline_um": [9, 9]}]}
        self.assertEqual(len(KF.findings({"t": t})), 1)
        many = {"outline_um": [1000, 1000], "hard_cores": [core(f"c{i}", 0, 0, 10, 10) for i in range(20)]}
        f = KF.findings({"t": many}, max_msgs=5)
        self.assertEqual(len(f), 6)
        self.assertIn("190 finding(s) in all", f[-1])


class Gates(unittest.TestCase):
    def test_pre_bind_gate_class_kitfit(self):
        import json, tempfile
        from pathlib import Path
        import plan_gate_pre as G
        t = {"outline_um": [100, 100], "hard_cores": [core("u_w", 10, 10, 20, 20, (0.684, 0.0)), core("u_e", 30, 10, 20, 20, (0.108, 0.0))]}
        p = Path(tempfile.mkdtemp()) / "plan.json"
        p.write_text(json.dumps({"partition_types": {"t": t}}))
        tree = Path(tempfile.mkdtemp())
        f = G.check(str(tree), str(p), skip=("SCHEMA", "INPUT", "TOOLS", "ROWS", "GEOM"))
        self.assertEqual(len(f), 1, f)
        self.assertTrue(f[0].startswith("FAIL KITFIT-OVERLAP type t"))
        self.assertEqual(G.check(str(tree), str(p), skip=("SCHEMA", "INPUT", "TOOLS", "ROWS", "GEOM", "KITFIT")), [])


class Outline(unittest.TestCase):
    def test_outline_core_margin(self):
        t = {"outline_um": [2885.76, 1226.88], "hard_cores": [core("u_ahi", 17.28, 1071.36, 432.0, 151.2, (0.108, 0.012))]}
        f = KF.findings({"t": t}, core_margin=KF.CORE_MARGIN_UM)
        self.assertEqual(len(f), 1, f)
        self.assertTrue(f[0].startswith("KITFIT-OUTLINE type t: u_ahi") and "0.012" in f[0], f)
        t["hard_cores"][0]["origin_um"][1] = 1071.216
        self.assertEqual(KF.findings({"t": t}, core_margin=KF.CORE_MARGIN_UM), [])
