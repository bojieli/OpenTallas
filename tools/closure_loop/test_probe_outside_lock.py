"""drive-0849 2026-10-10: a capacity check never ssh-probes a host while holding FLEET_LOCK."""
import sys, time, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent))
import closure_loop as cl  # noqa: E402


class ProbeOutsideLock(unittest.TestCase):
    def test_under_lock_uses_last_good(self):
        f = cl.Fleet()
        calls = []
        def once(h):
            calls.append((h, cl.FLEET_LOCK._is_owned()))
            return dict(load1=1.0, mem_gb=500, disk_gb=900)
        with patch.object(f, "_probe_once", side_effect=once):
            f.probe("ot-epyc2")                                   # fresh, outside the lock
            f.probe_cache["ot-epyc2"] = (time.time() - 100, f.probe_cache["ot-epyc2"][1])   # expire the 45 s cache
            with cl.FLEET_LOCK:
                info = f.probe("ot-epyc2")
        self.assertEqual(calls, [("ot-epyc2", False)])            # no ssh under the lock
        self.assertEqual(info["mem_gb"], 500)

    def test_fits_refreshes_outside_lock(self):
        f = cl.Fleet()
        seen = []
        def once(h):
            seen.append(cl.FLEET_LOCK._is_owned())
            return dict(load1=1.0, mem_gb=500, disk_gb=900, roots_gb={})
        with patch.object(f, "_probe_once", side_effect=once):
            try:
                f.fits("ot-epyc2", 8, 32, "j")
            except Exception:
                pass
        self.assertTrue(seen and seen[0] is False)


if __name__ == "__main__":
    unittest.main()
