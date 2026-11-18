import os, tempfile, time, unittest
import kit_slim as K

def mk(p, data=b"x", age=3600):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f: f.write(data)
    t = time.time() - age
    os.utime(p, (t, t))
    return p

class Guard:
    def __init__(self, bad=()): self.bad = bad
    def refuse(self, p, *a): return "protected" if any(b in p for b in self.bad) else None

class T(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.base = self.d + "/items/I/attempt_%d/gen/run/results/base"

    def run_(self, apply=True, guard=None, ptext="", exported=(), min_age=600):
        c = K.Ctx(apply, guard, None, ptext, min_age, exported)
        return K.run([self.d], c)

    def test_substage_hardlink_and_scale(self):
        b = self.base % 1
        big = b"a" * (2 * K.MB)
        for n in ("2_1_floorplan.odb", "2_floorplan.odb", "3_3_place_gp.odb", "3_place.odb", "5_route.odb", "5_3_fillcell.odb", "6_final.odb"):
            mk(b + "/" + n, big if n[0] in "56" else n.encode() * K.MB)
        mk(b + "/3_4_place_resized.odb", b"z")   # no successor needed? 3_place exists -> removed
        c = self.run_()
        self.assertFalse(os.path.exists(b + "/2_1_floorplan.odb"))
        self.assertFalse(os.path.exists(b + "/3_3_place_gp.odb"))
        self.assertTrue(os.path.exists(b + "/2_floorplan.odb") and os.path.exists(b + "/3_place.odb"))
        self.assertEqual(os.stat(b + "/5_route.odb").st_ino, os.stat(b + "/6_final.odb").st_ino)
        self.assertTrue(os.path.exists(b + "/5_3_fillcell.odb"))
        self.assertGreater(c.freed["dup_hardlink"], 3 * K.MB)

    def test_substage_kept_without_successor(self):
        b = self.base % 1
        mk(b + "/3_3_place_gp.odb", b"a" * K.MB)
        self.run_()
        self.assertTrue(os.path.exists(b + "/3_3_place_gp.odb"))

    def test_dry_run_touches_nothing(self):
        b = self.base % 1
        mk(b + "/2_1_floorplan.odb"); mk(b + "/2_floorplan.odb", b"y")
        c = self.run_(apply=False)
        self.assertTrue(os.path.exists(b + "/2_1_floorplan.odb"))

    def test_old_attempt_keeps_logs_only(self):
        o, n = self.base % 1, self.base % 2
        mk(o + "/6_final.odb", b"a" * (9 * K.MB)); mk(o + "/6_final.log", b"l" * (9 * K.MB)); mk(o + "/small.json", b"{}")
        mk(n + "/6_final.odb", b"a" * (9 * K.MB))
        self.run_()
        self.assertFalse(os.path.exists(o + "/6_final.odb"))
        self.assertTrue(os.path.exists(o + "/6_final.log") and os.path.exists(o + "/small.json"))
        self.assertTrue(os.path.exists(n + "/6_final.odb"))

    def test_exported_item_newest_slimmed(self):
        n = self.base % 1
        mk(n + "/6_final.odb", b"a" * (9 * K.MB))
        self.run_(exported={"I"})
        self.assertFalse(os.path.exists(n + "/6_final.odb"))

    def test_live_attempt_and_guard_skip(self):
        n = self.base % 1
        mk(n + "/2_1_floorplan.odb"); mk(n + "/2_floorplan.odb", b"y")
        self.run_(ptext="python " + self.d + "/items/I/attempt_1/gen")
        self.assertTrue(os.path.exists(n + "/2_1_floorplan.odb"))
        self.run_(guard=Guard(["2_1_floor"]))
        self.assertTrue(os.path.exists(n + "/2_1_floorplan.odb"))

    def test_recent_files_untouched(self):
        n = self.base % 1
        mk(n + "/2_1_floorplan.odb", age=10); mk(n + "/2_floorplan.odb", b"y", age=5)
        self.run_()
        self.assertTrue(os.path.exists(n + "/2_1_floorplan.odb"))

    def test_yosys_meta_gzip(self):
        n = self.base % 1
        mk(n + "/1_2_yosys_native_metadata.json", b"{" + b" " * (65 * K.MB) + b"}")
        c = self.run_()
        self.assertFalse(os.path.exists(n + "/1_2_yosys_native_metadata.json"))
        self.assertTrue(os.path.exists(n + "/1_2_yosys_native_metadata.json.gz"))

if __name__ == "__main__":
    unittest.main()
