"""drive-resume 2026-10-09: a bench whose log is empty (silent exit-code check) is judged on rc, not retried as unreadable."""
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import closure_loop as cl


class EmptyLog(unittest.TestCase):
    J = dict(host="h", run="/r", stage_tag="bench_x.a1b1")

    def test_empty_log_passes_on_rc0(self):
        with patch.object(cl, "ssh", return_value=SimpleNamespace(returncode=0, stdout="OT_BENCH_LOG_READ\n")):
            self.assertTrue(cl.bench_outcome(dict(self.J), dict(key="b", expect="pass"), 0))

    def test_unread_log_still_raises(self):
        with patch.object(cl, "ssh", return_value=SimpleNamespace(returncode=1, stdout="")), patch.object(cl.time, "sleep"):
            with self.assertRaises(RuntimeError):
                cl.bench_outcome(dict(self.J), dict(key="b", expect="pass"), 0)


if __name__ == "__main__":
    unittest.main()
