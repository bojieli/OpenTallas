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

if __name__ == "__main__":
    unittest.main()
