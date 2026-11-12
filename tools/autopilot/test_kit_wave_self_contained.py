#!/usr/bin/env python3
"""KW-FIX-45 11-12: KIT_NOT_SELF_CONTAINED classification (owner ruling: a job relying on files outside its folder is a kit failure)."""
import os, sys, unittest, subprocess, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit_wave as kw

class T(unittest.TestCase):
    def test_outside_path(self):
        t = "FileNotFoundError: [Errno 2] No such file or directory: '/srv/opentallas-scratch2/claude/kw45/src_qc_s27/physical/x/sidecar_pv.json'"
        self.assertEqual(kw.kit_not_self_contained(t), "/srv/opentallas-scratch2/claude/kw45/src_qc_s27/physical/x/sidecar_pv.json")
        cls, why = kw.classify("kit_topology", t)
        self.assertEqual(cls, "FLOW"); self.assertIn("KIT_NOT_SELF_CONTAINED", why)

    def test_own_folder_is_not_flagged(self):
        t = "FileNotFoundError: [Errno 2] No such file or directory: '/srv/o/claude/w/items/slw_x/attempt_3/gen/slw_x/config.mk'"
        self.assertEqual(kw.kit_not_self_contained(t), "")
        cls, why = kw.classify("place", t)
        self.assertNotIn("KIT_NOT_SELF_CONTAINED", why)

    def test_lister(self):
        with tempfile.TemporaryDirectory() as d:
            K = os.path.join(d, "kit"); os.makedirs(K)
            open(os.path.join(K, "config.mk"), "w").write(f"export A = {K}/x.v\nexport B = /srv/opentallas-scratch2/claude/other/y.lef\n")
            r = subprocess.run([sys.executable, "-I", "-c", kw.SELFCONT_PY, K, d], capture_output=True, text=True)
            rows = [l for l in r.stdout.splitlines() if l.startswith("SELFCONT\t")]
            self.assertEqual(len(rows), 1); self.assertTrue(rows[0].endswith("/srv/opentallas-scratch2/claude/other/y.lef"))

if __name__ == "__main__":
    unittest.main()
