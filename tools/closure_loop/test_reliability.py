"""Small local regression vehicles; no fleet, git, Docker, or route launches."""
import copy
import json
import multiprocessing as mp
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import closure_loop as cl


def advancing_worker(name, entered, release):
    def in_flight(j, fleet):
        entered.set()
        if not release.wait(5):
            raise AssertionError("test did not release worker")
        j.update(status="RUNNING", host="new-host", run="/new-run", stage_tag="calibrate.a2")
    with patch.object(cl, "step", in_flight):
        cl.advance_job(name, None)


def cancelling_worker(name, started, done, calls):
    def remote(host, script, **kwargs):
        calls.put((host, script))
    with patch.object(cl, "ssh", remote), patch.object(cl, "ledger"), patch.object(cl, "experiment"):
        started.set()
        cl.cmd_cancel(SimpleNamespace(name=name))
        done.set()


class ReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = patch.object(cl, "STATE", Path(self.tmp.name))
        self.state.start()
        self.addCleanup(self.state.stop)
        self.j = dict(name="race", status="READY", spec={"block": "block", "stages": {}, "verdict": {}}, events=[])
        cl.save_job(self.j)

    def test_cancel_survives_stale_save_and_new_worker(self):
        stale = copy.deepcopy(self.j)
        with patch.object(cl, "ledger"), patch.object(cl, "experiment"):
            cl.cmd_cancel(SimpleNamespace(name="race"))
        stale["status"] = "SYNC"
        cl.save_job(stale)
        self.assertEqual(stale["status"], "CANCELLED")
        with patch.object(cl, "step") as step:
            cl.advance_job("race", None)
        step.assert_not_called()
        self.assertEqual(cl.load_job("race")["status"], "CANCELLED")

    def test_cancel_serializes_with_remote_launch_and_reads_new_stage(self):
        ctx = mp.get_context("fork")
        entered, release, started, done = [ctx.Event() for _ in range(4)]
        calls = ctx.Queue()
        worker = ctx.Process(target=advancing_worker, args=("race", entered, release))
        cancel = ctx.Process(target=cancelling_worker, args=("race", started, done, calls))
        worker.start()
        try:
            self.assertTrue(entered.wait(5))
            cancel.start()
            self.assertTrue(started.wait(5))
            self.assertFalse(done.wait(.1), "cancel must wait for the in-flight transition")
            release.set()
            worker.join(5)
            cancel.join(5)
            self.assertEqual(worker.exitcode, 0)
            self.assertEqual(cancel.exitcode, 0)
            host, script = calls.get(timeout=1)
            self.assertEqual(host, "new-host")
            self.assertIn("/new-run/cl/calibrate.a2.pid", script)
            self.assertEqual(cl.load_job("race")["status"], "CANCELLED")
        finally:
            release.set()
            for proc in (worker, cancel):
                if proc.is_alive():
                    proc.terminate()
                if proc.pid:
                    proc.join(5)

    def test_remote_cancel_error_does_not_resurrect_job(self):
        self.j.update(host="host", run="/run", stage_tag="route.a1")
        cl.save_job(self.j)
        with patch.object(cl, "ssh", side_effect=RuntimeError("unreachable")):
            with self.assertRaises(RuntimeError):
                cl.cmd_cancel(SimpleNamespace(name="race"))
        self.assertEqual(cl.load_job("race")["status"], "CANCELLED")

    def test_legacy_requeue_has_no_side_effects_for_cancelled_or_stale_snapshot(self):
        self.j.update(status="NEEDS_HUMAN", attempt=2, stage_idx=0,
                      crashes=[dict(stage="calibrate", tail="no ORFS base", why="rc=3")])
        self.j["spec"].update(source={"commit": "fb5bc706e"},
                              stages={"calibrate": {"cmd": "true", "base": "/base"}})
        stale = copy.deepcopy(self.j)
        self.j["status"] = "CANCELLED"
        cl.save_job(self.j)
        for snapshot in (copy.deepcopy(self.j), stale):
            with patch.object(cl, "ledger") as ledger, patch.object(cl, "experiment") as experiment, \
                    patch.object(cl, "save_job") as save, patch.object(cl, "event") as event:
                cl.auto_requeue([snapshot])
            for side_effect in (ledger, experiment, save, event):
                side_effect.assert_not_called()
        self.assertEqual(cl.load_job("race")["status"], "CANCELLED")

    def test_legacy_requeue_still_handles_eligible_flow_failure(self):
        self.j.update(status="NEEDS_HUMAN", attempt=2, stage_idx=0,
                      crashes=[dict(stage="calibrate", tail="no ORFS base", why="rc=3")])
        self.j["spec"].update(source={"commit": "fb5bc706e"},
                              stages={"calibrate": {"cmd": "true", "base": "/base"}})
        cl.save_job(self.j)
        with patch.object(cl, "ledger"), patch.object(cl, "experiment"):
            cl.auto_requeue([self.j])
        j = cl.load_job("race")
        self.assertEqual((j["status"], j["attempt"]), ("READY", 3))

    def test_cancelled_job_cannot_be_retried(self):
        self.j["status"] = "CANCELLED"
        cl.save_job(self.j)
        with self.assertRaises(SystemExit):
            cl.cmd_retry(SimpleNamespace(name="race"))

    def test_restore_requires_ledger_and_preserves_live_work_and_old_state(self):
        ledger = Path(self.tmp.name) / "ledger.md"
        ledger.write_text("other job cancelled\n")
        self.j.update(status="RUNNING", host="host", run="/run", stage_tag="calibrate.a2")
        cl.save_job(self.j)
        before = cl.jpath("race").read_bytes()
        with patch.object(cl, "LEDGER", ledger), patch.object(cl, "ssh") as remote:
            with self.assertRaises(SystemExit):
                cl.cmd_restore_cancelled(SimpleNamespace(name="race"))
            self.assertEqual(cl.jpath("race").read_bytes(), before)
            ledger.write_text("- time | race | block @ sha | CANCELLED by a human | host:/run\n")
            with patch.object(cl, "ledger"):
                cl.cmd_restore_cancelled(SimpleNamespace(name="race"))
            remote.assert_not_called()
        restored = cl.load_job("race")
        self.assertEqual(restored["status"], "CANCELLED")
        recovery = restored["cancel_recovery"]
        self.assertEqual(Path(recovery["backup"]).read_bytes(), before)
        self.assertEqual(recovery["preserved_stage"]["stage_tag"], "calibrate.a2")

    def test_eco_uses_ordered_measured_overlays_even_when_spec_empty(self):
        self.j.update(host="host", run="/run")
        m = dict(ss_ps=190.49, ff_ps=-70.99, post_sdc=["generated/signoff.sdc", "generated/ff.sdc"])
        fleet = Mock()
        fleet.fits.return_value = (True, "ok")
        with patch.object(cl, "eco_paths", return_value=("/route", "/signoff")), \
                patch.object(cl, "ship_helpers"), patch.object(cl, "launch_stage") as launch, \
                patch.object(cl, "experiment"):
            self.assertTrue(cl.start_hold_eco(self.j, fleet, m))
        self.assertTrue(launch.call_args.args[2].endswith("generated/signoff.sdc generated/ff.sdc"))
        self.assertEqual(self.j["eco"]["post_sdc"], m["post_sdc"])

    def test_recorded_empty_overlays_do_not_add_unmeasured_constraints(self):
        self.j.update(host="host", run="/run")
        self.j["spec"]["verdict"]["post_sdc"] = ["unused.sdc"]
        fleet = Mock()
        fleet.fits.return_value = (True, "ok")
        for metrics, expected in ((dict(ss_ps=50, ff_ps=0, post_sdc=[]), []),
                                  (dict(ss_ps=50, ff_ps=0), ["unused.sdc"])):
            with patch.object(cl, "eco_paths", return_value=("/route", "/signoff")), \
                    patch.object(cl, "ship_helpers"), patch.object(cl, "launch_stage"), \
                    patch.object(cl, "experiment"):
                cl.start_hold_eco(self.j, fleet, metrics)
            self.assertEqual(self.j["eco"]["post_sdc"], expected)

    def test_failed_eco_never_installs_or_replaces_original_metrics(self):
        original = dict(ss_ps=190.49, ff_ps=-70.99, drc=0)
        failed = dict(ss_ps=-340500.58, ff_ps=-59.43, drc=0, cells_added=0, errors=[])
        self.j.update(status="ECO", host="host", run="/run", metrics=original,
                      eco={"pre": original.copy(), "tried": True})
        with patch.object(cl, "stage_list", return_value=[]), \
                patch.object(cl, "poll_stage", return_value=("RC", 0)), \
                patch.object(cl, "ssh", return_value=SimpleNamespace(stdout=json.dumps(failed))), \
                patch.object(cl, "summarize_failure", return_value=True), patch.object(cl, "ledger"), \
                patch.object(cl, "launch_stage") as launch, patch.object(cl, "eco_install_cmd") as install:
            cl.step(self.j, Mock())
        launch.assert_not_called()
        install.assert_not_called()
        self.assertEqual(self.j["metrics"], original)
        self.assertEqual(self.j["eco"]["result"], failed)
        self.assertNotIn("installed", self.j["eco"])

    def test_eco_verdict_fails_closed(self):
        passing = dict(ss_ps=15, ff_ps=15, drc=0, errors=[])
        self.assertTrue(cl.eco_passes(passing, 0))
        for bad in (None, {}, dict(passing, ss_ps=None), dict(passing, ss_ps=float("inf")),
                    dict(passing, ff_ps=float("nan")), dict(passing, ss_ps=True),
                    dict(passing, drc=None), dict(passing, drc=False), dict(passing, errors=["STA error"]),
                    dict(passing, ff_ps=14.99)):
            self.assertFalse(cl.eco_passes(bad, 0), bad)
        self.assertFalse(cl.eco_passes(passing, 9))

    def test_existing_eco_evidence_is_not_removed(self):
        out = Path(self.tmp.name) / "eco"
        out.mkdir()
        evidence = out / "result.json"
        evidence.write_bytes(b"immutable failed verdict\n")
        run = subprocess.run(["bash", str(cl.HERE / "hold_eco.sh"), "/route", "/signoff", str(out), "block"],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 10)
        self.assertEqual(evidence.read_bytes(), b"immutable failed verdict\n")


if __name__ == "__main__":
    unittest.main()
