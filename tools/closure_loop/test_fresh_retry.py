"""drive-0849 2026-10-10: a human retry drops a stale checkpoint resume / HOLD-STOP caps unless --keep-resume."""
import sys, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent))
import closure_loop as cl  # noqa: E402


class FreshRetry(unittest.TestCase):
    def _run(self, keep):
        j = cl.JobState(name="x", status="EARLY_FAIL_HOLD", attempt=3, host="h", commit_full="c", stage_idx=2, stage_key="route",
                        spec={"name": "x"}, resume={"kind": "hold_stop", "at": "t"}, hold_stop={"cts": 9000}, events=[])
        saved = {}
        with patch.object(cl, "load_job", return_value=j), patch.object(cl, "save_job", side_effect=lambda x: saved.update(x)), \
                patch.object(cl, "ledger"), patch.object(cl, "job_lock", return_value=tempfile.TemporaryFile()), \
                patch.object(cl, "log", create=True):
            cl.cmd_retry(SimpleNamespace(name="x", at=None, keep_resume=keep))
        return saved

    def test_drops(self):
        s = self._run(False)
        self.assertNotIn("resume", s); self.assertNotIn("hold_stop", s); self.assertEqual(s["attempt"], 4)
        self.assertEqual(s["status"], "SYNC")                     # re-sync: a released job has no src/

    def test_keep(self):
        s = self._run(True)
        self.assertIn("resume", s); self.assertIn("hold_stop", s)


if __name__ == "__main__":
    unittest.main()
