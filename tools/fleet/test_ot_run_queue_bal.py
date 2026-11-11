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
    # LOADGATE_1110 (ot-heavy load gate) is covered by test_ot_run_load_gate.py; these cases pin the older rules with the gate off
    m.LOAD_GATE_FACTOR = 0
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


class RefusedSource(unittest.TestCase):
    """QUEUE-BAL-2 20:4x: epyc4 scratch2 100% (26 GB < 50 GB floor) held the only copy of the kits; ot-run said 'NOT RUN: no
    host qualifies' without trying SPILL while epyc5/epyc6 admitted 1.4 TB."""
    D = "/srv/x/claude/l/k"

    def setUp(self):
        self.m = load()

    def refused_row(self, gb=26):
        return dict(row(225, 62.0, 256), disk_gb=gb, scratch_disk="/srv/opentallas-scratch", scratch_disk_gb=gb)

    def place(self, probes, disk=20):
        with patch.object(self.m, "probe", side_effect=lambda h, d: (h, probes[h][1])), \
             patch.object(self.m, "trigger_reaper", return_value=False), contextlib.redirect_stderr(io.StringIO()):
            return self.m.place(list(probes), self.D, disk, 48, quiet=True)

    def test_place_records_disk_refused_host_with_dir(self):
        ok = self.place(dict(epyc4=(None, self.refused_row()), epyc5=(None, None)))
        self.assertEqual(ok, {})
        self.assertEqual(list(self.m.REFUSED_SRC), ["epyc4"])
        self.assertIn("scratch disk", self.m.PLACE_NOTES["epyc4"])

    def test_place_ignores_hosts_without_dir_or_other_refusals(self):
        big = dict(row(225, 62.0, 256), total_gb=40)          # physically too small: not a disk refusal
        ok = self.place(dict(epyc5=(None, None), epyc6=(None, dict(error="unreachable")), intel1=(None, big)))
        self.assertEqual(ok, {})
        self.assertEqual(self.m.REFUSED_SRC, {})

    def test_place_clears_between_calls(self):
        self.place(dict(epyc4=(None, self.refused_row())))
        self.place(dict(epyc4=(None, row(225, 62.0, 256))))
        self.assertEqual(self.m.REFUSED_SRC, {})

    def main(self, refused, plan, argv_extra=(), spill_rc=0, spill_seq=None, gb=26, plans=None):
        def place(hosts, d, disk, mem, quiet=False):
            self.m.REFUSED_SRC.clear()
            if refused:
                self.m.REFUSED_SRC["epyc4"] = self.refused_row(gb)
                self.m.PLACE_NOTES["epyc4"] = "scratch disk /srv/opentallas-scratch has 26 GB free < floor 50 GB"
            return {}
        runs = iter(spill_seq or [spill_rc])
        err = io.StringIO()
        with patch.object(self.m, "HOSTS", ["epyc4", "epyc5"]), patch.object(self.m, "place", side_effect=place), \
             patch.object(self.m, "reload_conf", return_value=[]), patch.object(self.m, "trigger_sweep"), \
             patch.object(self.m, "held_hosts", return_value={}), patch.object(self.m.time, "sleep"), \
             patch.object(self.m, "retryable_queued_probe_failures", return_value=set()), \
             patch.object(self.m, "spill_plan", **(dict(side_effect=plans) if plans else dict(return_value=plan))) as splan, \
             patch.object(self.m, "spill_run", side_effect=lambda *a, **k: next(runs)) as srun, \
             patch.object(self.m.sys, "argv", ["ot-run", "--mem", "48", "--threads", "8", *argv_extra, "--dir", self.D, "--", "true"]), \
             patch.dict(os.environ, {}, clear=True), contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit) as ex:
                self.m.main()
        return ex.exception.code, splan, srun, err.getvalue()

    def test_refused_dir_host_spills_to_free_host(self):
        code, splan, srun, err = self.main(True, (("epyc5", [self.D], 2.7), "", False))
        self.assertEqual(code, 0)
        self.assertEqual(splan.call_args.args[0], "epyc4")
        self.assertEqual(srun.call_args.args[:2], ("epyc4", "epyc5"))
        self.assertIn("REFUSED-SOURCE SPILL", err)

    def test_unadmitted_refused_spill_places_again(self):
        code, splan, srun, _ = self.main(True, (("epyc5", [self.D], 2.7), "", False), spill_seq=[None, 7])
        self.assertEqual(code, 7)
        self.assertEqual(srun.call_count, 2)

    def test_no_spill_host_now_waits_instead_of_not_run(self):
        plans = [(None, "no spill host admits it now", False), (("epyc5", [self.D], 2.7), "", False)]
        code, splan, srun, err = self.main(True, None, plans=plans)
        self.assertEqual(code, 0)
        self.assertEqual(splan.call_count, 2)
        self.assertIn("re-placing every", err)

    def test_permanent_refusal_still_not_run(self):
        code, _, srun, err = self.main(True, (None, "command names /srv/y outside the --stage paths", True))
        self.assertIn("no host qualifies", str(code))
        self.assertFalse(srun.called)

    def test_pinned_job_is_not_spilled(self):
        code, splan, srun, _ = self.main(True, (("epyc5", [self.D], 2.7), "", False), argv_extra=("--hosts", "epyc4"))
        self.assertIn("no host qualifies", str(code))
        self.assertFalse(splan.called or srun.called)

    def test_too_little_room_for_back_copy_waits(self):
        code, splan, srun, err = self.main(True, (("epyc5", [self.D], 2.7), "", False), argv_extra=("--max-wait", "1"), gb=2)
        self.assertFalse(splan.called or srun.called)
        self.assertIn("for the back-copy", err)

    def test_no_refused_host_keeps_old_not_run(self):
        code, splan, _, _ = self.main(False, (("epyc5", [self.D], 2.7), "", False))
        self.assertIn("no host qualifies", str(code))
        self.assertFalse(splan.called)


if __name__ == "__main__":
    unittest.main()
