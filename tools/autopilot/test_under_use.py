import unittest

import under_use as UU

STATUS = ("ot-run status: epyc2 admits 400 GB (avail 500, x) load 23/128 run 4 threads 20/128 | "
          "epyc10 admits 100 GB (avail 120, x) load 177/96 waiters 3:90 GB run 34 threads 96/96 | "
          "localhost admits 700 GB (avail 800, x) load 3/112 run 0 | next 16-thread 32 GB job -> epyc2")
CFG = {"dies": {"s81": {"hold_items": {"*": "tree_switch WAIT-PDN: old form"}},
                "kv": {"hold_items": {"io_cor": "WAVE-HOLDS-1115 stop list"}}}}
ITEMS = {
    "a": {"die": "s81", "item": "t1", "status": "ENQUEUED"},
    "b": {"die": "s81", "item": "t2", "status": "ENQUEUED"},
    "c": {"die": "kv", "item": "io_cor", "status": "ENQUEUED"},
    "d": {"die": "kv", "item": "other", "status": "ENQUEUED"},
    "e": {"die": "s81", "item": "t3", "status": "ROUTE-HELD", "route_hold": "WAIT-VISUAL no verdict"},
    "f": {"die": "s81", "item": "t4", "status": "ROUTE-HELD", "route_hold": "tree_switch old PDN"},
    "g": {"die": "kv", "item": "z", "status": "RUNNING"},
    "h": {"die": "kv", "item": "y", "status": "FAIL"},
}


class UnderUse(unittest.TestCase):
    def test_host_idle(self):
        h = UU.host_idle(STATUS)
        self.assertEqual(h["epyc2"]["idle"], 105)       # 128 - max(load 23, committed 20)
        self.assertEqual(h["epyc10"]["idle"], 0)        # over-committed: never negative
        self.assertNotIn("localhost", h)

    def test_holds(self):
        c = UU.hold_counts(ITEMS, CFG)
        self.assertEqual(c["tree_switch"], 3)           # two held ENQUEUED rows + one ROUTE-HELD naming tree_switch
        self.assertEqual(c["hold_items:WAVE-HOLDS-1115"], 1)
        self.assertEqual(c["route_hold:WAIT-VISUAL"], 1)
        self.assertEqual(c["enqueued_not_held"], 1)
        self.assertEqual(sum(c.values()), 6)            # RUNNING / FAIL rows are not counted

    def test_line(self):
        s = UU.line(STATUS, ITEMS, CFG)
        self.assertTrue(s.startswith("UNDER-USE idle 105 of 224 threads (used 53%)"), s)
        self.assertIn("epyc2=105(load 23/128, thr 20)", s)
        self.assertIn("rows not launching 6: tree_switch=3", s)

    def test_no_status_or_state(self):
        self.assertTrue(UU.line("", {}, {}).startswith("UNDER-USE idle 0 of 0 threads"))

    def test_step_logs_once_and_never_raises(self):
        logs = []

        class AP:
            AP_DIR = "/nonexistent-ap-dir"
            OT_RUN = "ot-run"
            log = staticmethod(logs.append)

            @staticmethod
            def sh(cmd, timeout=0):
                return 0, STATUS, ""
        UU.step(AP)
        self.assertEqual(len(logs), 1)
        self.assertTrue(logs[0].startswith("UNDER-USE idle"))
        AP.sh = staticmethod(lambda cmd, timeout=0: (1, "", "x"))
        UU.step(AP)
        self.assertEqual(logs[1], "UNDER-USE ot-run --status unavailable")


if __name__ == "__main__":
    unittest.main()
