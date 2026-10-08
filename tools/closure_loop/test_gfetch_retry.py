import subprocess, sys, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent))
import closure_loop as C


class GfetchRetry(unittest.TestCase):
    def test_retries_and_updates_tracking_ref(self):
        calls = []
        def fake(cmd, timeout=600, **kw):
            calls.append(cmd)
            return subprocess.CompletedProcess(cmd, 1 if len(calls) == 1 else 0, "", "cannot lock ref")
        with patch.object(C, "sh", fake), patch.object(C.time, "sleep"), patch.object(C, "log") as log:
            r = C.gfetch("main")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(len(calls), 2)
        self.assertIn("+refs/heads/main:refs/remotes/origin/main", calls[0])
        log.assert_not_called()

    def test_logs_persistent_failure(self):
        fake = lambda cmd, timeout=600, **kw: subprocess.CompletedProcess(cmd, 128, "", "fatal: boom")
        with patch.object(C, "sh", fake), patch.object(C.time, "sleep"), patch.object(C, "log") as log:
            r = C.gfetch("main", tries=2)
        self.assertEqual(r.returncode, 128)
        log.assert_called_once()


if __name__ == "__main__":
    unittest.main()
