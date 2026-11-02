"""Exercise bounded small-stage admission against a saturated host."""
import os
import subprocess
import unittest
from pathlib import Path
from test_ot_heavy_crit import Heavy


class ShortPool(Heavy):
    def setUp(self):
        super().setUp()
        self.old = os.environ.get("OT_HEAVY_THREADS")
        os.environ["OT_HEAVY_THREADS"] = "2"

    def tearDown(self):
        if self.old is None:
            os.environ.pop("OT_HEAVY_THREADS", None)
        else:
            os.environ["OT_HEAVY_THREADS"] = self.old

    # Base load-cap assertions expect non-small requests; keep them in their original suite.
    def test_at_cap_non_crit_waits(self):
        os.environ["OT_HEAVY_THREADS"] = "3"
        super().test_at_cap_non_crit_waits()

    def test_short_bypasses_load_without_cpu_priority(self):
        r, a = self.run_("500")
        self.assertIsNotNone(a, r.stderr)
        self.assertNotIn("CPUWeight=1000", a)
        self.assertIn("SHORT_POOL slot", (self.d / "state/admit.log").read_text())

    def test_busy_pool_waits(self):
        import fcntl
        state = self.d / "state"
        state.mkdir()
        leases = [(state / f"short.{i}.lock").open("a") for i in range(1, 17)]
        try:
            for lease in leases:
                fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
            r, a = self.run_("500")
            self.assertIsNone(a)
            self.assertEqual(r.returncode, 75)
            self.assertIn("short pool: all", r.stderr)
        finally:
            for lease in leases:
                lease.close()

    def test_memory_rejection_still_waits(self):
        self.rec.write_text('#!/bin/bash\n[ "$1" = --is-die ] && exit 1; echo "NO 4 cls | insufficient memory"\n')
        r, a = self.run_("500")
        self.assertIsNone(a)
        self.assertEqual(r.returncode, 75)
        self.assertIn("insufficient memory", r.stderr)

    def test_pool_opt_out(self):
        os.environ["OT_HEAVY_SHORT_POOL"] = "0"
        try:
            r, a = self.run_("500")
        finally:
            os.environ.pop("OT_HEAVY_SHORT_POOL", None)
        self.assertIsNone(a)
        self.assertEqual(r.returncode, 75)


if __name__ == "__main__":
    unittest.main()
