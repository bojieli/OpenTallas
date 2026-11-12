#!/usr/bin/env python3
"""KW-FIX-45 11-12: plan_package materialises a plan folder (links followed, copied) and bind can refuse linked siblings."""
import os, sys, json, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plan_package as PP

class T(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); d = self.t.name
        self.other = os.path.join(d, "other"); os.makedirs(os.path.join(self.other, "cores"))
        open(os.path.join(self.other, "die_io.json"), "w").write('{"a": 1}')
        open(os.path.join(self.other, "cores", "c.json"), "w").write("{}")
        self.plan_dir = os.path.join(d, "lane"); os.makedirs(self.plan_dir)
        open(os.path.join(self.plan_dir, "die_plan.json"), "w").write(json.dumps({"partition_types": {}}))
        os.symlink(os.path.join(self.other, "die_io.json"), os.path.join(self.plan_dir, "die_io.json"))
        os.symlink(os.path.join(self.other, "cores"), os.path.join(self.plan_dir, "cores"))
        self.plan = os.path.join(self.plan_dir, "die_plan.json")

    def tearDown(self):
        self.t.cleanup()

    def test_gate_modes(self):
        ok, msg = PP.gate(self.plan, "warn"); self.assertTrue(ok); self.assertIn("not self-contained", msg)
        ok, msg = PP.gate(self.plan, "require"); self.assertFalse(ok)
        ok, msg = PP.gate(self.plan, "off"); self.assertTrue(ok); self.assertEqual(msg, "")

    def test_package_is_self_contained_and_verified(self):
        out = os.path.join(self.t.name, "pkg")
        meta = PP.package(self.plan, out)
        self.assertEqual(set(meta["files"]), {"die_plan.json", "die_io.json", "cores/c.json"})
        self.assertFalse(os.path.islink(os.path.join(out, "die_io.json")))
        self.assertEqual(PP.verify(out), [])
        ok, msg = PP.gate(os.path.join(out, "die_plan.json"), "require"); self.assertTrue(ok, msg)
        open(os.path.join(out, "die_io.json"), "w").write('{"a": 2}')          # drift after packaging
        self.assertTrue(any(r == "die_io.json" for r, _ in PP.verify(out)))
        ok, _ = PP.gate(os.path.join(out, "die_plan.json"), "require"); self.assertFalse(ok)

class AbsPaths(unittest.TestCase):
    def test_abs_path_value_fails_verify_and_package_rewrites(self):
        with tempfile.TemporaryDirectory() as d:
            other = os.path.join(d, "foreign.json"); open(other, "w").write('{"bins": []}')
            lane = os.path.join(d, "lane"); os.makedirs(lane)
            plan = os.path.join(lane, "die_plan.json")
            json.dump({"partition_types": {"t": {"clock": {"sink_bins_file": other}}}}, open(plan, "w"))
            ok, msg = PP.gate(plan, "require"); self.assertFalse(ok); self.assertIn("absolute path", msg)
            out = os.path.join(d, "pkg"); PP.package(plan, out)
            v = json.load(open(os.path.join(out, "die_plan.json")))["partition_types"]["t"]["clock"]["sink_bins_file"]
            self.assertTrue(v.startswith("_ext/")); self.assertTrue(os.path.isfile(os.path.join(out, v)))
            self.assertEqual(PP.verify(out), [])
            ok, msg = PP.gate(os.path.join(out, "die_plan.json"), "require"); self.assertTrue(ok, msg)

    def test_missing_abs_path_fails_package(self):
        with tempfile.TemporaryDirectory() as d:
            lane = os.path.join(d, "lane"); os.makedirs(lane)
            plan = os.path.join(lane, "die_plan.json")
            json.dump({"x": "/srv/nowhere/a/b.json"}, open(plan, "w"))
            with self.assertRaises(SystemExit): PP.package(plan, os.path.join(d, "pkg"))

    def test_taps_input_path_prefers_plan_folder(self):
        import taps
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "sink_bins")); open(os.path.join(d, "sink_bins", "t.json"), "w").write("{}")
            rel = "physical/die_plan/x/plan_of_record/sink_bins/t.json"
            self.assertEqual(str(taps.input_path(rel, d)), os.path.join(d, "sink_bins", "t.json"))
            self.assertEqual(str(taps.input_path("/a/b/c.json", d)), "/a/b/c.json")
            self.assertEqual(taps.input_path(rel, os.path.join(d, "none")), taps._root() / rel)


if __name__ == "__main__":
    unittest.main()
