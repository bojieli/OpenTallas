"""el1013-fleet3 2026-10-13: nothing on the daemon's dispatch thread may wait for the publish lock or run one git
process per CLOSED job (29 READY jobs sat 30 min on 448 GB of idle memory)."""
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import closure_loop as cl


class DispatchNotBlocked(unittest.TestCase):
    def test_publish_measured_does_not_wait_for_the_publish_lock(self):
        with tempfile.TemporaryDirectory() as d, patch.object(cl, "STATE", Path(d)):
            (Path(d) / "measured.dirty").write_text("x")
            done = threading.Event()
            self.assertTrue(cl.PUBLISH_LOCK.acquire(blocking=False))
            try:
                t = threading.Thread(target=lambda: (cl.publish_measured(), done.set()), daemon=True)
                t.start()
                self.assertTrue(done.wait(5), "publish_measured waited for PUBLISH_LOCK")
            finally:
                cl.PUBLISH_LOCK.release()
            self.assertTrue((Path(d) / "measured.dirty").exists())      # still pending: retried next tick
            self.assertFalse((Path(d) / "measured.published").exists())

    def test_on_main_uses_one_rev_list_per_main_sha(self):
        with tempfile.TemporaryDirectory() as d:
            g = lambda *a: subprocess.run(["git", "-C", d, "-c", "user.name=t", "-c", "user.email=t@t", *a],
                                          capture_output=True, text=True, check=True).stdout.strip()
            g("init", "-q")
            g("commit", "-q", "--allow-empty", "-m", "a")
            a = g("rev-parse", "HEAD")
            g("commit", "-q", "--allow-empty", "-m", "b")
            main = g("rev-parse", "HEAD")
            g("checkout", "-q", "-b", "side", a)
            g("commit", "-q", "--allow-empty", "-m", "c")
            side = g("rev-parse", "HEAD")
            ev = {"sha": main}
            with patch.object(cl, "REPO", Path(d)):
                self.assertTrue(cl._on_main(a[:9], ev))
                real, calls = subprocess.run, []
                with patch.object(cl.subprocess, "run", side_effect=lambda *x, **k: (calls.append(x), real(*x, **k))[1]):
                    self.assertTrue(cl._on_main(a, ev))
                    self.assertTrue(cl._on_main(main[:7], ev))
                    self.assertFalse(cl._on_main(side[:12], ev))
                self.assertEqual(calls, [])

    def test_tick_runs_disk_release_off_the_dispatch_thread(self):
        import inspect
        src = inspect.getsource(cl.tick)
        for name in ("release_bulk(", "release_deep(", "stale24_sweep("):
            self.assertNotIn(name, src)
        self.assertIn("schedule_housekeeping()", src)


if __name__ == "__main__":
    unittest.main()
