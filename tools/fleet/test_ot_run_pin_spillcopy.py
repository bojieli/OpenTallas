"""PINSPILL_1114: an explicit single-host --hosts pin ignores the .ot-run-spill-copy marker; unpinned placement still refuses it."""
import importlib.machinery, importlib.util, pathlib, unittest
from unittest import mock

P = str(pathlib.Path(__file__).with_name("ot-run"))
loader = importlib.machinery.SourceFileLoader("ot_run_pinspill", P)
M = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_run_pinspill", loader))
loader.exec_module(M)
ROW = dict(disk_gb=500, ncpu=96, admit_gb=100, free_gb=100, total_gb=1000, avail_gb=116, cpu_load1=10, fresh=0)


class PinSpill(unittest.TestCase):
    def seen(self, hosts):
        calls = []
        def fake(h, d, spill_ok=False):
            calls.append(spill_ok)
            return h, (ROW if spill_ok else None)
        with mock.patch.object(M, "probe", fake), mock.patch.object(M, "trigger_reaper", lambda *a: False):
            ok = M.place(hosts, "/srv/opentallas-scratch2/claude/lane", 20, 48, quiet=True)
        return calls, ok

    def test_single_host_pin_accepts_a_spill_marked_root(self):
        calls, ok = self.seen(["epyc9"])
        self.assertEqual(calls, [True]); self.assertIn("epyc9", ok)

    def test_unpinned_host_list_still_refuses_it(self):
        calls, ok = self.seen(M.HOSTS)
        self.assertTrue(not any(calls)); self.assertEqual(ok, {})


if __name__ == "__main__":
    unittest.main()
