"""OVERLOAD_1114 (ADMIT-TUNE-1): placement steers away from a host above OVERLOAD_RATIO x cores while another eligible host is below it."""
import importlib.machinery
import importlib.util
import pathlib
import unittest

P = str(pathlib.Path(__file__).with_name("ot-run"))
loader = importlib.machinery.SourceFileLoader("ot_run_overload", P)
M = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_run_overload", loader))
loader.exec_module(M)


def row(load, ncpu=96, admit=300, free=300):
    return dict(cpu_load1=load, ncpu=ncpu, admit_gb=admit, free_gb=free, total_gb=1000, avail_gb=admit + 16, fresh=0, host="h")


class Overload(unittest.TestCase):
    def setUp(self):
        M.LOAD_GATE_FACTOR = 0   # the ot-heavy load gate is removed on the fleet (ADMIT-TUNE-1); placement balances by OVERLOAD_RATIO instead
        for k in ("OT_RUN_DIRECT", "OT_RUN_CRIT"):
            M.os.environ.pop(k, None)

    def test_overloaded_host_is_skipped_when_a_calmer_one_admits(self):
        # epyc10 4.5x with the most free memory, epyc8 1.5x: the old score() already preferred the calmer host; the cap makes it a rule
        h, q = M.choose({"epyc10": row(434, admit=500), "epyc8": row(140, admit=100)}, 48, 8)
        self.assertEqual((h, q), ("epyc8", False))

    def test_all_overloaded_still_places_somewhere(self):
        h, q = M.choose({"epyc10": row(434), "epyc7": row(300)}, 48, 8)
        self.assertIn(h, ("epyc10", "epyc7"))

    def test_queued_job_goes_to_a_host_that_is_not_overloaded(self):
        h, q = M.choose({"epyc10": row(434, admit=10, free=400), "epyc8": row(140, admit=10, free=50)}, 48, 8)
        self.assertEqual((h, q), ("epyc8", True))

    def test_spill_destination_may_be_loaded_up_to_half_the_source(self):
        self.assertAlmostEqual(M.spill_dst_ratio(4.5), 2.25)
        self.assertAlmostEqual(M.spill_dst_ratio(1.4), 0.85)  # max(0.85, 0.7) capped by source minus gap 0.9
        self.assertAlmostEqual(M.spill_dst_ratio(1.2), 0.7)


if __name__ == "__main__":
    unittest.main()
