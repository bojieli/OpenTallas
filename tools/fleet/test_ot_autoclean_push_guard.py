import importlib.util, os, tempfile, time, unittest
sp = importlib.util.spec_from_file_location("ac", os.path.join(os.path.dirname(os.path.abspath(__file__)), "ot-autoclean.py"))
ac = importlib.util.module_from_spec(sp); sp.loader.exec_module(ac)


class PushGuard(unittest.TestCase):
    def test_stale_or_missing_coord_is_not_fresh(self):
        d = tempfile.mkdtemp(); os.makedirs(d + "/autopilot")
        self.assertFalse(ac.push_coord_fresh(d))
        p = d + "/autopilot/kit_wave.json"; open(p, "w").write("{}")
        self.assertTrue(ac.push_coord_fresh(d))
        os.utime(p, (time.time() - 7200, time.time() - 7200))
        self.assertFalse(ac.push_coord_fresh(d))
        self.assertTrue(ac.push_coord_fresh(d, now=os.path.getmtime(p) + 60))
