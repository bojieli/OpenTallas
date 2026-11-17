"""OT_RUN_SCRATCH_DISK_FLOOR_GB may only raise the scratch floor: below 50 GB it is refused and logged (COORD 11-17)."""
import importlib.machinery, importlib.util, io, pathlib, contextlib, unittest

P = str(pathlib.Path(__file__).with_name("ot-run"))
loader = importlib.machinery.SourceFileLoader("ot_run_floor", P)
M = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_run_floor", loader))
loader.exec_module(M)


class Floor(unittest.TestCase):
    def call(self, v, **kw):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            r = M.clamp_floor(v, "X", **kw)
        return r, err.getvalue()

    def test_below_minimum_is_refused_and_logged(self):
        for v in ("10", "0", "49", "-5"):
            r, e = self.call(v)
            self.assertEqual(r, 50); self.assertIn("FLOOR-OVERRIDE refused", e)

    def test_raising_is_allowed_silently(self):
        for v, want in (("50", 50), ("80", 80), (" 150 ", 150)):
            r, e = self.call(v); self.assertEqual((r, e), (want, ""))

    def test_garbage_falls_back_and_logs(self):
        r, e = self.call("abc"); self.assertEqual(r, 50); self.assertIn("not a number", e)

    def test_module_floor_and_host_map_use_it(self):
        self.assertGreaterEqual(M.SCRATCH_DISK_FLOOR_GB, 50)
        self.assertTrue(all(v >= 50 for v in M.SCRATCH_DISK_FLOOR_GB_HOSTS.values()))
