"""SENTINEL-SLACK (drive-1010 2026-10-10): +1e16 'no constrained path' slack is never a pass."""
import inspect
import math
import unittest

import closure_loop as cl


class Sentinel(unittest.TestCase):
    def test_real_slack(self):
        for v in (0.0, 15.2, -3.0, 999999.0):
            self.assertTrue(cl.real_slack(v), v)
        for v in (1e16, -1e16, 1e6, math.inf, math.nan, None, True, "5"):
            self.assertFalse(cl.real_slack(v), v)

    def test_eco_result_with_sentinel_fails(self):
        ok = dict(tt_ps=5.0, ff_ps=3.0, drc=0)
        self.assertTrue(cl.eco_passes(ok, 0))
        self.assertFalse(cl.eco_passes(dict(ok, tt_ps=1e16), 0))
        self.assertFalse(cl.eco_passes(dict(ok, ff_ps=1e16), 0))

    def test_every_verdict_closure_guards_sentinels(self):
        src = inspect.getsource(cl)
        self.assertNotIn("closed = ss >= SS_MIN", src)
        self.assertNotIn('mclosed = mr["tt"] >= SS_MIN', src)
        self.assertGreaterEqual(src.count("real_slack(ss) and real_slack(ff) and ss >= SS_MIN"), 2)


if __name__ == "__main__":
    unittest.main()


class UnderConstrained(unittest.TestCase):
    def test_census(self):
        self.assertIsNone(cl.under_constrained({"registers": 5000, "registers_clocked": 4990}))
        self.assertIn("only 0 of 5000", cl.under_constrained({"registers": 5000, "registers_clocked": 0}))
        self.assertIsNotNone(cl.under_constrained({"registers": 5000, "registers_clocked": 30}))   # < 1 % = 50
        self.assertIsNone(cl.under_constrained({"registers": 5000, "registers_clocked": 50}))
        self.assertIsNotNone(cl.under_constrained({"registers": 200, "registers_clocked": 3}))     # < 10
        self.assertIsNone(cl.under_constrained({"registers": 4, "registers_clocked": 4}))         # tiny block: all clocked
        self.assertIsNone(cl.under_constrained({"registers": 0, "registers_clocked": 0}))         # pure wiring
        self.assertIsNone(cl.under_constrained({}))                                                # no census (old run)

    def test_verdict_and_measured_paths_use_it(self):
        src = inspect.getsource(cl)
        self.assertIn('failed.append("UNDER-CONSTRAINED")', src)
        self.assertIn('mclosed = not uc and', src)

    def test_meas_resta_emits_census(self):
        import pathlib
        t = (pathlib.Path(cl.__file__).parent / "meas_resta.py").read_text()
        self.assertIn('OT_REGS_CLOCKED', t)
        self.assertIn('registers_clocked=', t)
