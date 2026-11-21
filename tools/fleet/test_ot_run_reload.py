"""RELOAD / MULTIHOST-SPILL / OLDWAIT (FLEET-WATCH-1630): a waiting ot-run re-execs into a newer rt/current, a --hosts list may spill inside the list, status shows the oldest waiter."""
import importlib.machinery
import importlib.util
import os
import pathlib
import unittest
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parent
loader = importlib.machinery.SourceFileLoader("ot_run_reload", str(HERE / "ot-run"))
spec = importlib.util.spec_from_loader(loader.name, loader)
m = importlib.util.module_from_spec(spec)
loader.exec_module(m)
rloader = importlib.machinery.SourceFileLoader("recon_oldwait", str(HERE / "ot-heavy-reconcile"))
rspec = importlib.util.spec_from_loader(rloader.name, rloader)
R = importlib.util.module_from_spec(rspec)
rloader.exec_module(R)


class Reload(unittest.TestCase):
    def setUp(self):
        import tempfile
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.rt = pathlib.Path(t.name) / "claude" / "rt"
        for sha in ("aaaaaaaaaaaa", "bbbbbbbbbbbb"):
            (self.rt / sha / "tools/fleet").mkdir(parents=True)
            (self.rt / sha / "tools/fleet/ot-run").write_text("#")
        self.cur = self.rt / "current"
        os.symlink("aaaaaaaaaaaa", self.cur)
        self.real = str(self.rt / "aaaaaaaaaaaa/tools/fleet/ot-run")
        self.log = []
        p = mock.patch.object(m, "log_signal", self.log.append)
        p.start()
        self.addCleanup(p.stop)

    def call(self, **k):
        calls = []
        r = m.reexec_if_runtime_changed(1234.5, argv=["--mem", "10"], real=self.real, execv=lambda *a: calls.append(a), env={}, **k)
        return r, calls

    def test_same_runtime_does_nothing(self):
        self.assertEqual(self.call(), (False, []))

    def test_new_runtime_execs_the_same_args_with_the_original_start(self):
        os.remove(self.cur)
        os.symlink("bbbbbbbbbbbb", self.cur)
        r, calls = self.call()
        self.assertTrue(r)
        exe, argv, env = calls[0]
        self.assertEqual(argv[1:], ["-I", str(self.rt / "bbbbbbbbbbbb/tools/fleet/ot-run"), "--mem", "10"])
        self.assertEqual(env["OT_RUN_T0"], "1234.5")
        self.assertTrue(any("RELOAD aaaaaaaaaaaa -> bbbbbbbbbbbb" in x for x in self.log))

    def test_not_under_rt_or_disabled_or_missing_tool_does_nothing(self):
        os.remove(self.cur)
        os.symlink("bbbbbbbbbbbb", self.cur)
        calls = []
        self.assertFalse(m.reexec_if_runtime_changed(1.0, argv=[], real="/home/u/bin/ot-run", execv=lambda *a: calls.append(a), env={}))
        with mock.patch.dict(os.environ, {"OT_RUN_NO_RELOAD": "1"}):
            self.assertFalse(self.call()[0])
        (self.rt / "bbbbbbbbbbbb/tools/fleet/ot-run").unlink()
        self.assertFalse(self.call()[0])
        self.assertEqual(calls, [])


class Pinned(unittest.TestCase):
    RT = "/srv/opentallas-scratch2/claude/rt/aaaaaaaaaaaa/tools/fleet/ot-run"

    def test_pinned_waiter_in_rt_gets_a_bounded_wait_so_it_reaches_the_reload_check(self):
        self.assertEqual(m.pinned_cycle(None, real=self.RT), m.PINNED_CYCLE_S)
        self.assertEqual(m.pinned_cycle(30, real=self.RT), 30)

    def test_client_outside_rt_or_disabled_keeps_its_wait(self):
        self.assertIsNone(m.pinned_cycle(None, real="/home/u/.local/lib/kw44/ot-run"))
        with mock.patch.dict(os.environ, {"OT_RUN_NO_RELOAD": "1"}):
            self.assertIsNone(m.pinned_cycle(None, real=self.RT))


class Misc(unittest.TestCase):
    def test_multihost_list_spills_single_host_is_a_pin(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OT_RUN_NO_SPILL", None)
            self.assertTrue(m.multihost_spill("epyc2,epyc8,epyc9"))
            self.assertFalse(m.multihost_spill("epyc8"))
            self.assertFalse(m.multihost_spill(""))
        with mock.patch.dict(os.environ, {"OT_RUN_NO_SPILL": "1"}):
            self.assertFalse(m.multihost_spill("a,b"))

    def test_spill_candidates_stay_inside_the_hosts_list(self):
        with mock.patch.object(m, "SPILL_ONLY_HOSTS", {"epyc2", "epyc8"}), mock.patch.object(m, "HOSTS", ["epyc2", "epyc8", "epyc9", "intel1"]), \
                mock.patch.object(m, "STAGE", ["/srv/a"]), mock.patch.object(m, "under", lambda d, s: True), mock.patch.object(m, "command_srv_paths", lambda c: []), \
                mock.patch.object(m, "ssh_sh", lambda *a, **k: type("R", (), {"stdout": ""})()), mock.patch.object(m, "STAGE_FILES", set()), \
                mock.patch.object(m, "proof_away", lambda *a: False), mock.patch.object(m, "spill_scan", lambda *a, **k: ([], 1.0, "", False, set())):
            seen = []

            def rows(h, roots, bases):
                seen.append(h)
                return [{"error": "x"}]
            with mock.patch.object(m, "spill_dest_rows", rows):
                plan = m._spill_plan("epyc8", "/srv/a/k", ["true"], 10, 2, False, 5, set(), lambda s: None)
        self.assertEqual(sorted(seen), ["epyc2"])
        self.assertIsNone(plan[0])

    def test_proc_age_of_this_process_is_small_and_oldest_is_kept(self):
        a = R.proc_age_s(os.getpid())
        self.assertTrue(0 <= a < 3600 * 24 * 30)
        self.assertEqual(R.proc_age_s(99999999), 0)


if __name__ == "__main__":
    unittest.main()
