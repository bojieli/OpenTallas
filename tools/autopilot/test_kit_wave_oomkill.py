"""OOMKILL_1114: an earlyoom SIGTERM/SIGKILL victim is class INFRA with an OOM reason (not exit 2) and matches the free-retry KILL_RE."""
import pathlib, sys, unittest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import kit_wave as K


class OomKill(unittest.TestCase):
    TEXTS = ["make: *** [Makefile:1: do-5_2_route] Error 241\nmake: *** [x] Error 2",
             "make: *** [do-5_3_fillcell] Error 247",
             "openroad terminated: earlyoom: sending SIGTERM rc 143",
             "step failed with rc=137 killed"]

    def test_victims_book_as_oom_infra_at_every_route_stage(self):
        for st in ("place", "cts", "global_route", "drt", "route", "kit_route"):
            for tx in self.TEXTS[:3]:
                cls, why = K.classify(st, tx)
                self.assertEqual(cls, "INFRA", (st, tx))
                self.assertIn("OOM", why)
                self.assertTrue(K.KILL_RE.search(why), why)        # -> the charge-free INFRA relaunch on another host

    def test_a_real_design_failure_is_not_swallowed(self):
        cls, _ = K.classify("route", "[ERROR GRT-0116] Global routing finished with congestion\nmake: *** [x] Error 2")
        self.assertNotEqual(cls, "INFRA")


if __name__ == "__main__":
    unittest.main()
