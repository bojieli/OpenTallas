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

    def test_recovery_does_not_duplicate_a_slow_worker(self):
        pool = Mock()
        slow = Mock()
        slow.done.return_value = False
        with patch.object(cl, "_RECOVERY_POOL", pool), patch.object(cl, "_RECOVERY_FUTURE", slow):
            cl.schedule_recovery()
            pool.submit.assert_not_called()
            slow.done.return_value = True
            cl.schedule_recovery()
            pool.submit.assert_called_once_with(cl.recover_jobs)

    def test_recovery_does_not_revive_superseded_failure(self):
        old = dict(name="old", status="NEEDS_RTL", spec={"block": "same"})
        live = dict(name="successor", status="RUNNING", spec={"block": "same"})
        alone = dict(name="recover", status="NEEDS_HUMAN", spec={"block": "other"})
        with patch.object(cl, "all_jobs", return_value=[old, live, alone]), \
             patch.object(cl, "reevaluate_benches") as bench, patch.object(cl, "requeue_toolchain"), \
             patch.object(cl, "requeue_budget"), patch.object(cl, "requeue_hold_only"), \
             patch.object(cl, "requeue_ssh_verdict"), patch.object(cl, "auto_requeue"):
            cl.recover_jobs()
        bench.assert_called_once_with([live, alone])

    def test_recovery_failure_does_not_skip_other_classes(self):
        with patch.object(cl, "all_jobs", return_value=[]), patch.object(cl, "log"), \
             patch.object(cl, "reevaluate_benches", side_effect=RuntimeError("network")), \
             patch.object(cl, "requeue_toolchain") as toolchain, patch.object(cl, "requeue_budget") as budget, \
             patch.object(cl, "requeue_hold_only") as hold, patch.object(cl, "requeue_ssh_verdict") as ssh, \
             patch.object(cl, "auto_requeue") as auto:
            cl.recover_jobs()
        for check in (toolchain, budget, hold, ssh, auto):
            check.assert_called_once_with([])

    def test_host_requirement_must_be_explicit_known_hosts(self):
        spec = dict(name="test", block="b", owner="o", source={"branch": "b", "commit": "c" * 40},
                    stages={"route": {"cmd": "true"}}, no_bench_reason="fixture")
        for bad in (True, False, "ot-epyc2", [], ["unknown-host"]):
            with self.subTest(value=bad):
                self.assertTrue(any("host_require" in e for e in cl.validate(dict(spec, host_require=bad))))
        self.assertFalse(any("host_require" in e for e in cl.validate(dict(spec, host_require=["ot-epyc2"]))))

    def test_failed_tool_probe_is_retried_without_hour_long_fleet_outage(self):
        fleet = cl.Fleet()
        fleet.tool_cache["host"] = (cl.time.time() - 16, None)
        with patch.object(cl, "ssh", return_value=SimpleNamespace(returncode=0, stdout="img_latest=pinned\n")) as ssh:
            self.assertEqual(fleet.toolchain("host"), {"img_latest": "pinned"})
            self.assertEqual(fleet.toolchain("host"), {"img_latest": "pinned"})
        ssh.assert_called_once()

    def test_adoption_hold_blocks_verdict_and_publish_without_stopping_route(self):
        hold = Path(self.tmp.name) / "adoption_holds" / "race.json"
        hold.parent.mkdir()
        hold.write_text(json.dumps({"reason": "exact gate pending"}))
        with patch.object(cl, "get_metrics") as metrics, patch.object(cl, "publish") as publish, \
             patch.object(cl, "kill_own_stage") as kill, patch.object(cl, "log"):
            cl.do_verdict(self.j, None, [])
            cl.do_commit(self.j)
        metrics.assert_not_called()
        publish.assert_not_called()
        kill.assert_not_called()
        self.assertEqual(self.j["status"], "READY")
        hold.unlink()
        self.assertFalse(cl.adoption_held(self.j))

    def test_mutation_bench_uses_private_source_for_cwd_and_explicit_src(self):
        run = Path(self.tmp.name) / "run"
        (run / "src").mkdir(parents=True)
        (run / "cl").mkdir()
        (run / "src" / "rtl.txt").write_text("golden")
        j = dict(self.j, host="remote", run=str(run), attempt=1, commit_full="c" * 40,
                 spec=dict(self.j["spec"], source={"commit": "c" * 40}))
        st = dict(key="bench_neg", kind="bench", threads=1)
        scripts = []
        def remote(host, command, **kw):
            if "input" in kw:
                scripts.append(kw["input"])
            return SimpleNamespace(stdout="", returncode=0)
        with patch.object(cl, "ssh", remote):
            cl.launch_stage(j, st, 'echo mutant > rtl.txt; test "$SRC" = "{SRC}"; test "{RUN}/src" = "$SRC"')
        result = subprocess.run(["bash", "-c", scripts[0]], cwd=run / "src", capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((run / "src" / "rtl.txt").read_text(), "golden")
        self.assertEqual((run / "bench_src_a1" / "rtl.txt").read_text(), "mutant\n")
        with patch.object(cl, "ssh", return_value=SimpleNamespace(stdout="", stderr="", returncode=0)) as ssh:
            self.assertTrue(cl.remote_ok(j, "test -f rtl.txt")[0])
        self.assertIn(f"cd {run}/bench_src_a1 &&", ssh.call_args.args[1])

    def test_unreadable_historical_bench_does_not_starve_recovery(self):
        first = dict(name="unreachable", status="NEEDS_RTL", spec={},
                     reason="bench_exact expected PASS but rc=0", stage_tag="bench_exact.a1")
        second = dict(first, name="available", benches={})
        stage = dict(key="bench_exact", expect="pass")
        for x in (first, second):   # STALE-SAVE 2026-10-09: the re-judgment re-reads the job file under its lock
            cl.save_job(copy.deepcopy(x))
        with patch.object(cl, "stage_list", return_value=[stage]), \
             patch.object(cl, "bench_outcome", side_effect=[RuntimeError("unreadable"), True]), \
             patch.object(cl, "save_job") as save, patch.object(cl, "log"), \
             patch.object(cl, "event"), patch.object(cl, "ledger"), patch.object(cl, "experiment"):
            cl.reevaluate_benches([first, second])
        self.assertEqual(first["status"], "NEEDS_RTL")
        self.assertNotIn("fix_requeued", first)
        save.assert_called_once()
        saved = save.call_args.args[0]
        self.assertEqual((saved["name"], saved["status"], saved["stage_idx"]), ("available", "READY", 1))

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

    def test_source_failure_retry_synchronizes_before_launch(self):
        for fields in ({}, {"commit_full": "a" * 40, "source_synced": False}):
            j = dict(self.j, status="NEEDS_HUMAN", host="host", attempt=1,
                     stage_idx=0, errors=["source unavailable"], **fields)
            cl.save_job(j)
            with patch.object(cl, "ledger"), patch.object(cl, "log"):
                cl.cmd_retry(SimpleNamespace(name="race"))
            restored = cl.load_job("race")
            self.assertEqual(restored["status"], "SYNC")
            self.assertEqual(restored["stage_idx"], 0)

    def test_legacy_broken_ready_state_cannot_launch_benches(self):
        j = dict(self.j, status="READY", host="host", stage_idx=0)
        with patch.object(cl, "bench_track") as benches, patch.object(cl, "log"):
            cl.step(j, None)
        benches.assert_not_called()
        self.assertEqual(j["status"], "SYNC")

    def test_stage_retry_preserves_synchronized_source(self):
        j = dict(self.j, status="NEEDS_HUMAN", host="host", attempt=1,
                 stage_idx=0, commit_full="a" * 40, source_synced=True)
        cl.save_job(j)
        with patch.object(cl, "ledger"), patch.object(cl, "log"):
            cl.cmd_retry(SimpleNamespace(name="race"))
        self.assertEqual(cl.load_job("race")["status"], "READY")

    def test_calibration_transport_failure_preserves_completed_stage(self):
        j = dict(self.j, status="RUNNING", host="host", run="/run", stage_idx=0)
        stages = [dict(key="calibrate", kind="calibrate")]
        with patch.object(cl, "stage_list", return_value=stages), \
             patch.object(cl, "bench_track", return_value=True), \
             patch.object(cl, "poll_stage", return_value=("DONE", 0)), \
             patch.object(cl, "remote_ok", return_value=(True, "")), \
             patch.object(cl, "ssh", return_value=SimpleNamespace(returncode=255, stdout="")), \
             patch.object(cl, "crash") as crash, patch.object(cl, "log"):
            cl.step(j, None)
        crash.assert_not_called()
        self.assertEqual((j["status"], j["stage_idx"]), ("RUNNING", 0))
        self.assertIn("artifact transport", j["wait"])

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
        passing = dict(ss_ps=cl.SS_MIN, ff_ps=cl.FF_MIN, drc=0, errors=[])
        self.assertTrue(cl.eco_passes(passing, 0))
        for bad in (None, {}, dict(passing, ss_ps=None), dict(passing, ss_ps=float("inf")),
                    dict(passing, ff_ps=float("nan")), dict(passing, ss_ps=True),
                    dict(passing, drc=None), dict(passing, drc=False), dict(passing, errors=["STA error"]),
                    dict(passing, ff_ps=cl.FF_MIN - 0.01)):
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
