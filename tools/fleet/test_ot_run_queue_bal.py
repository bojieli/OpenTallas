"""QUEUE-BAL-1 2026-11-05: spilled waiters re-place after REQUEUE_S; placement respects the ot-heavy load cap.

Bug (COORD 19:2x): 122 waiters (5.9 TB) sat on intel1 for up to 9.6 h; 96 were kit PLACE jobs SPILLED epyc4 -> intel1.
choose() said intel1 "admits 171 GB now" but its ot-heavy holds every non-crit job while load1 >= 1.5 x nproc (intel1 at
198-241 on 112 cores), and spill_run() waited on the spill host with no bound, so those waiters never moved again."""
import contextlib
import importlib.machinery
import importlib.util
import io
import os
import pathlib
import tempfile
import unittest
from unittest.mock import patch

HERE = pathlib.Path(__file__).resolve().parent


def load():
    loader = importlib.machinery.SourceFileLoader("ot_run_qb", str(HERE / "ot-run"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    m = importlib.util.module_from_spec(spec)
    loader.exec_module(m)
    return m


def row(admit, load, ncpu, free=None):
    return dict(admit_gb=admit, free_gb=admit if free is None else free, cpu_load1=load, ncpu=ncpu, total_gb=1000,
                disk_gb=1000, avail_gb=admit, headroom_gb=0, floor_gb=50, waiting=0, waiting_gb=0, running=1, fresh=0)


class LoadCap(unittest.TestCase):
    def setUp(self):
        self.m = load()
        self.env = patch.dict(os.environ, {}, clear=False)
        self.env.start()
        os.environ.pop("OT_RUN_CRIT", None)

    def tearDown(self):
        self.env.stop()

    def test_capped_host_of_19_2x(self):
        self.assertTrue(self.m.load_capped(row(171, 198.0, 112), 48, 8))      # intel1: 198 >= 168
        self.assertFalse(self.m.load_capped(row(91, 126.0, 256), 48, 8))      # epyc4: 126 < 384
        self.assertTrue(self.m.load_capped(row(160, 192.0, 128), 48, 8))      # epyc2: 192 >= 192 (ot-heavy uses >=)

    def test_crit_and_short_jobs_bypass_the_cap(self):
        os.environ["OT_RUN_CRIT"] = "1"
        self.assertFalse(self.m.load_capped(row(171, 241.0, 112), 48, 8))
        os.environ.pop("OT_RUN_CRIT")
        self.assertFalse(self.m.load_capped(row(171, 241.0, 112), 10, 2))      # ot-heavy short pool
        self.assertTrue(self.m.load_capped(row(171, 241.0, 112), 10, 4))

    def test_factor_zero_disables(self):
        self.m.LOAD_CAP_FACTOR = 0
        self.assertFalse(self.m.load_capped(row(171, 999.0, 112), 48, 8))

    def test_reserve_threads_do_not_lower_the_cap(self):
        # localhost HOST_RESERVE (8 threads): ot-heavy caps on nproc 112 -> 168, not on 104 -> 156
        r = self.m.reserved("localhost", row(224, 160.0, 112))
        self.assertFalse(self.m.load_capped(r, 48, 8))
        r = self.m.reserved("localhost", row(224, 170.0, 112))
        self.assertTrue(self.m.load_capped(r, 48, 8))

    def test_choose_skips_capped_host_with_memory(self):
        best, queue = self.m.choose(dict(intel1=row(171, 241.0, 112), epyc4=row(91, 126.0, 256)), 48, 8)
        self.assertEqual((best, queue), ("epyc4", False))

    def test_choose_all_capped_queues_on_memory(self):
        best, queue = self.m.choose(dict(intel1=row(171, 241.0, 112), epyc2=row(100, 203.0, 128)), 48, 8)
        self.assertEqual((best, queue), ("intel1", True))

    def test_crit_job_still_runs_on_capped_host(self):
        os.environ["OT_RUN_CRIT"] = "1"
        best, queue = self.m.choose(dict(intel1=row(171, 241.0, 112)), 48, 8)
        self.assertEqual((best, queue), ("intel1", False))


class SpillRequeue(unittest.TestCase):
    def setUp(self):
        self.m = load()
        self.tmp = tempfile.TemporaryDirectory()
        self.m.SPILL_PENDING = os.path.join(self.tmp.name, "pending")
        self.m.SIGNAL_LOG = os.path.join(self.tmp.name, "signals.log")
        self.calls = []

    def tearDown(self):
        self.tmp.cleanup()

    def spill(self, max_wait, run_result):
        ok = type("R", (), dict(returncode=0, stderr="", sent=3))()

        def run(host, mem, cmd, d=None, max_wait=None, env="", quiet=False, quiet_notrun=False, on_start=None, disk=None):
            self.calls.append((host, max_wait, quiet_notrun))
            return run_result
        with patch.object(self.m, "spill_copy_fwd", return_value=ok), patch.object(self.m, "ssh_sh"), \
             patch.object(self.m, "run", side_effect=run), patch.dict(os.environ, {}, clear=False):
            os.environ.pop(self.m.HANDOFF_ENV, None)
            out = []
            rc = self.m.spill_run("epyc4", "intel1", ["/srv/x/claude/l/k"], 0.1, 48, ["true"], "/srv/x/claude/l/k",
                                  max_wait, out.append)
        return rc, out

    def test_unadmitted_spill_is_replaced_after_requeue(self):
        rc, out = self.spill(None, (75, False))
        self.assertIsNone(rc)
        self.assertEqual(self.calls, [("intel1", self.m.REQUEUE_S, True)])
        self.assertTrue(any("REBALANCE" in x for x in out), out)
        self.assertEqual(os.listdir(self.m.SPILL_PENDING), [])            # no pending record left for an unstarted job

    def test_callers_max_wait_still_ends_not_run(self):
        rc, _ = self.spill(30, (75, False))
        self.assertEqual(rc, 75)
        self.assertEqual(self.calls, [("intel1", 30, False)])

    def test_ssh_failure_is_not_a_rebalance(self):
        rc, _ = self.spill(None, (255, False))
        self.assertEqual(rc, 255)

    def test_capped_dir_host_with_memory_spills(self):
        """REFILL-0325 shape under the cap: --dir only on a host at 289/128 that admits memory -> SPILL, not a wait there"""
        rows = dict(epyc4=row(300, 289.0, 128))
        with patch.object(self.m, "HOSTS", ["epyc4", "intel1"]), patch.object(self.m, "place", return_value=rows), \
             patch.object(self.m, "trigger_sweep"), patch.object(self.m, "held_hosts", return_value={}), \
             patch.object(self.m, "spill_plan", return_value=(("intel1", ["/k"], 0.1), "", False)) as splan, \
             patch.object(self.m, "spill_run", return_value=0) as srun, \
             patch.object(self.m.sys, "argv", ["ot-run", "--mem", "48", "--threads", "8", "--dir", "/srv/x/claude/l/k", "--", "true"]), \
             patch.dict(os.environ, {}, clear=True), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as ex:
                self.m.main()
        self.assertEqual(ex.exception.code, 0)
        self.assertTrue(splan.called and srun.called)
        self.assertEqual(srun.call_args.args[1], "intel1")

    def test_main_places_again_after_unadmitted_spill(self):
        """queue branch: spill_run None -> the job waits on the source for REQUEUE_S, then the next spill runs it"""
        rows = dict(epyc4=row(10, 126.0, 256))
        spills = iter([None, 0])
        plans = []
        runs = []

        def run(host, mem, cmd, d=None, max_wait=None, env="", quiet=False, quiet_notrun=False, disk=None):
            runs.append((host, max_wait))
            return 75, False
        with patch.object(self.m, "HOSTS", ["epyc4", "intel1"]), patch.object(self.m, "reload_conf", return_value=[]), \
             patch.object(self.m, "place", return_value=rows), patch.object(self.m, "trigger_sweep"), \
             patch.object(self.m, "held_hosts", return_value={}), \
             patch.object(self.m, "spill_plan", side_effect=lambda *a, **k: (plans.append(1) or (("intel1", ["/k"], 0.1), "", False))), \
             patch.object(self.m, "spill_run", side_effect=lambda *a, **k: next(spills)), \
             patch.object(self.m, "run", side_effect=run), \
             patch.object(self.m.sys, "argv", ["ot-run", "--mem", "48", "--threads", "8", "--dir", "/srv/x/claude/l/k", "--", "true"]), \
             patch.dict(os.environ, {}, clear=True), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as ex:
                self.m.main()
        self.assertEqual(ex.exception.code, 0)
        self.assertEqual(len(plans), 2)
        self.assertEqual(runs, [("epyc4", self.m.REQUEUE_S)])


if __name__ == "__main__":
    unittest.main()
