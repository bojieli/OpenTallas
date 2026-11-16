"""THREADCAP_1116 (COORD 11-16): ot-run placement counts the committed --threads of running jobs per host."""
import importlib.machinery
import importlib.util
import pathlib
import unittest

P = str(pathlib.Path(__file__).with_name("ot-run"))
loader = importlib.machinery.SourceFileLoader("ot_run_thread_cap", P)
M = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_run_thread_cap", loader))
loader.exec_module(M)


def row(load, committed=None, ncpu=96, admit=300):
    r = dict(cpu_load1=load, ncpu=ncpu, admit_gb=admit, free_gb=admit, total_gb=1000, avail_gb=admit + 16, fresh=0, host="h")
    if committed is not None:
        r["committed_threads"] = committed
    return r


class ThreadCap(unittest.TestCase):
    def setUp(self):
        M.LOAD_GATE_FACTOR = 0
        M.THREAD_CAP = 1.0
        for k in ("OT_RUN_DIRECT", "OT_RUN_CRIT", "OT_RUN_PRIO_ENV"):
            M.os.environ.pop(k, None)

    def test_free_threads(self):
        self.assertEqual(M.free_threads(row(0, 40)), 56)
        self.assertIsNone(M.free_threads(row(0)))        # older probe: no field
        M.THREAD_CAP = 0
        self.assertIsNone(M.free_threads(row(0, 40)))

    def test_most_free_threads_wins_even_when_load1_lags(self):
        # epyc10 load1 reads 20 (a burst not shown yet) but 96 threads are committed; epyc2 has 105 free
        h, q = M.choose({"epyc10": row(20, 96, admit=500), "epyc2": row(23, 23, ncpu=128, admit=100)}, 48, 16)
        self.assertEqual((h, q), ("epyc2", False))

    def test_host_with_room_beats_host_without_even_with_more_memory(self):
        h, _ = M.choose({"a": row(10, 90, admit=900), "b": row(10, 10, admit=100)}, 48, 16)
        self.assertEqual(h, "b")

    def test_all_over_still_places_on_the_least_over_host(self):
        h, q = M.choose({"a": row(10, 200), "b": row(10, 120)}, 48, 16)
        self.assertEqual((h, q), ("b", False))

    def test_rows_without_the_field_keep_the_old_order(self):
        h, _ = M.choose({"a": row(10, admit=500), "b": row(300, admit=500)}, 48, 16)
        self.assertEqual(h, "a")

    def test_plan_job_exempt(self):
        M.os.environ["OT_RUN_PRIO_ENV"] = "OT_HEAVY_PRIO=plan"
        try:
            h, q = M.choose({"a": row(10, 200, admit=500), "b": row(10, 0, admit=100)}, 48, 16)
        finally:
            M.os.environ.pop("OT_RUN_PRIO_ENV")
        self.assertEqual(q, False)   # plan path: quietest CPU among hosts with the memory, never held by the thread count


if __name__ == "__main__":
    unittest.main()
