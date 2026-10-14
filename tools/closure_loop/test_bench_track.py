"""Parallel bench track (OWNER 2026-10-07 05:00): benches beside calibrate/route, verdict gated, failure stops the route.
Local only: ssh / launches / polls are mocked."""
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import closure_loop as cl

SPEC = dict(name="t", block="b", owner="o", source=dict(commit="c" * 40), stages=dict(
    bench=[dict(name="exact", cmd="true", expect="pass"), dict(name="neg", cmd="false", expect="fail")],
    route=dict(cmd="route")))


class Fleet:
    own_running = {}

    def fits(self, *a):
        return True, "ok"

    def launched(self, *a, **kw):
        pass

    def _launched(self, *a, **kw):
        pass

    def launch_complete(self, *a):
        pass

    def probe(self, *a):
        return {}


def job(**kw):
    j = dict(name="t", spec=SPEC, status="READY", stage_idx=0, attempt=1, benches={}, events=[], host="h", run="/r",
             commit_full="c" * 40, created="2026-10-07T06:00", retries_used=0, hosts_tried=["h"])
    j.update(kw)
    return j


class BenchTrack(unittest.TestCase):
    def run_track(self, j, polls, outcome=True):
        launched = []

        def launch(v, st, cmd):
            v["stage_tag"] = f"{st['key']}.a{v['attempt']}"
            launched.append(v["stage_tag"])
        with patch.object(cl, "launch_stage", launch), patch.object(cl, "poll_stage", side_effect=polls), \
                patch.object(cl, "remote_ok", return_value=(True, "")), patch.object(cl, "stage_tail", return_value=""), \
                patch.object(cl, "bench_outcome", return_value=outcome), patch.object(cl, "kill_own_stage") as kill, \
                patch.object(cl, "ledger"), patch.object(cl, "experiment"), patch.object(cl, "log"):
            stl = cl.stage_list(SPEC)
            cl.bench_par_decide(j, stl)
            j["status"] = j.pop("then_status", j["status"])
            for _ in range(len(polls) + 2):
                if not cl.bench_track(j, Fleet(), stl):
                    break
        return launched, kill

    def test_parallel_and_main_track_starts_at_route(self):
        j = job()
        launched, _ = self.run_track(j, [("RC", 0), ("RC", 1)])
        self.assertTrue(j["bench_par"])
        self.assertEqual(cl.stage_list(SPEC)[j["stage_idx"]]["kind"], "route")
        self.assertEqual(len(launched), 2)
        self.assertTrue(cl.benches_done(j, cl.stage_list(SPEC)))

    def test_failure_stops_route_and_needs_rtl(self):
        j = job(then_status="RUNNING")       # the route is running when the bench fails
        _, kill = self.run_track(j, [("RC", 3)], outcome=False)
        self.assertEqual(j["status"], "NEEDS_RTL")
        kill.assert_called_once()

    def test_bench_first_opt_out_and_started_jobs(self):
        spec = dict(SPEC, bench_first=True)
        j = job(spec=spec)
        cl.bench_par_decide(j, cl.stage_list(spec))
        self.assertFalse(j["bench_par"])
        self.assertEqual(j["stage_idx"], 0)
        j2 = job(stage_tag="bench_exact.a1")
        with patch.object(cl, "log"):
            cl.bench_par_decide(j2, cl.stage_list(SPEC))
        self.assertFalse(j2["bench_par"])

    def test_verdict_waits_for_benches(self):
        j = job(bench_par=True, btrack={}, stage_idx=len(cl.stage_list(SPEC)) - 1)
        stl = cl.stage_list(SPEC)
        j["stage_idx"] = next(i for i, x in enumerate(stl) if x["kind"] == "verdict")
        with patch.object(cl, "bench_track", return_value=True), patch.object(cl, "do_verdict") as dv, \
                patch.object(cl, "log"):
            cl.step(j, Fleet())
        dv.assert_not_called()
        self.assertEqual(j["wait"], "benches")

    def test_missing_predecessor_does_not_starve_running_completion(self):
        j = job(bench_par=True, btrack={"bench_neg": dict(
            state="running", host="producer", run="/producer", tag="neg.a1", n=1)})
        launched = []
        def launch(v, st, cmd):
            launched.append(st["key"])
            v["stage_tag"] = "exact.a2"
        with patch.object(cl, "poll_stage", return_value=("RC", 1)) as poll, \
                patch.object(cl, "remote_ok", return_value=(True, "")), \
                patch.object(cl, "stage_tail", return_value="expected mutant failure"), \
                patch.object(cl, "bench_outcome", return_value=True), \
                patch.object(cl, "launch_stage", side_effect=launch), patch.object(cl, "log"):
            self.assertTrue(cl.bench_track(j, Fleet(), cl.stage_list(SPEC)))
        self.assertEqual(poll.call_args.args[0]["run"], "/producer")
        self.assertTrue(j["benches"]["bench_neg"]["ok"])
        self.assertEqual(j["btrack"]["bench_neg"]["state"], "done")
        self.assertEqual(launched, ["bench_exact"])

    def test_route_keys_allow_three(self):
        keys = {"b@c": ["a", "b"]}
        self.assertIsNone(cl.route_key_full(keys, "b@c", "x"))
        keys["b@c"].append("x")
        self.assertIsNotNone(cl.route_key_full(keys, "b@c", "y"))
        self.assertIsNone(cl.route_key_full(keys, "b@c", "a"))


class VacuousPass(unittest.TestCase):
    def test_work(self):
        self.assertEqual(cl.bench_work("PASS compared=0 checks: 0")[0], False)
        self.assertEqual(cl.bench_work("PASS compared=12")[0], True)
        self.assertIsNone(cl.bench_work("all good")[0])
        self.assertEqual(cl.bench_work("reducer results 0", r"reducer results (\d+)")[0], False)
        self.assertEqual(cl.bench_work("reducer results 7", r"reducer results (\d+)")[0], True)
        self.assertEqual(cl.bench_work("nothing", r"reducer results (\d+)")[0], False)


class Watchdog(unittest.TestCase):
    def test_quiet_output_never_kills_or_restarts_work(self):
        import time, datetime as dt
        old = (dt.datetime.now().astimezone() - dt.timedelta(hours=4)).isoformat()
        j = job(status="RUNNING", stage_started=old)
        st = dict(key="calibrate")
        quiet = SimpleNamespace(returncode=0, stdout="END\n")
        with patch.object(cl, "ssh", return_value=quiet), patch.object(cl, "kill_own_stage") as kill, \
                patch.object(cl, "ledger"), patch.object(cl, "experiment"), patch.object(cl, "log"):
            cl.stuck_watchdog(j, st)
            self.assertEqual(j["status"], "RUNNING")
            j.update(wd_checked=0)
            cl.stuck_watchdog(j, st)
        self.assertEqual(j["status"], "RUNNING")
        kill.assert_not_called()
        self.assertTrue(j["quiet_output_reported"])

    def test_growing_log_is_left_alone(self):
        import datetime as dt
        old = (dt.datetime.now().astimezone() - dt.timedelta(hours=4)).isoformat()
        j = job(status="RUNNING", stage_started=old)
        with patch.object(cl, "ssh", return_value=SimpleNamespace(returncode=0, stdout="/r/x.log\nEND\n")), \
                patch.object(cl, "kill_own_stage") as kill:
            cl.stuck_watchdog(j, dict(key="route"))
        self.assertEqual(j["status"], "RUNNING")
        kill.assert_not_called()


class BenchCrash(unittest.TestCase):
    def test_positive_bench_bus_error_is_a_crash(self):
        st = dict(expect="pass")
        self.assertTrue(cl.bench_crashed(st, 1, "g++: internal compiler error: Bus error (program cc1plus)"))
        self.assertTrue(cl.bench_crashed(st, 135, ""))
        self.assertFalse(cl.bench_crashed(st, 1, "mismatch at word 7\nFAIL"))
        self.assertFalse(cl.bench_crashed(st, 134, "compared=4000 errors=3 abort"))


class Transient(unittest.TestCase):
    def test_classify(self):
        import subprocess
        self.assertTrue(cl.is_transient(subprocess.TimeoutExpired(["ssh", "-o", "x", "h", "bash -s"], 300)))
        self.assertTrue(cl.is_transient(RuntimeError("command failed rc=255: ssh h")))
        self.assertFalse(cl.is_transient(KeyError("metrics")))

    def test_backoff_then_move(self):
        import subprocess
        j = job(status="READY", stage_tag=None, hosts_tried=["h"])
        stl = cl.stage_list(SPEC)
        j["stage_idx"] = next(i for i, x in enumerate(stl) if x["kind"] == "bench")
        fleet = SimpleNamespace(choose=lambda spec, exclude: ("h2", None), launched=lambda *a, **kw: None)
        ex = subprocess.TimeoutExpired(["ssh", "h"], 300)
        with patch.object(cl, "log"), patch.object(cl, "experiment"), \
                patch.object(cl, "host_cfg", return_value=dict(label="H", base="/b")):
            self.assertTrue(cl.handle_transient(j, fleet, ex))
            self.assertEqual(j["host"], "h")
            cl.handle_transient(j, fleet, ex)
            cl.handle_transient(j, fleet, ex)
        self.assertEqual((j["host"], j["status"]), ("h2", "SYNC"))

    def test_ready_route_moves_after_three(self):
        """2026-10-11: a never-launched route job on an overloaded host (ssh timeouts) moves and re-calibrates"""
        import subprocess
        spec = dict(SPEC, stages=dict(SPEC["stages"], calibrate=dict(cmd="cal", base="/b/x")))
        stl = cl.stage_list(spec)
        cal = next(i for i, x in enumerate(stl) if x["kind"] == "calibrate")
        rt = next(i for i, x in enumerate(stl) if x["kind"] == "route")
        self.assertGreater(rt, cal)
        j = job(spec=spec, status="READY", stage_tag=None, stage_idx=rt, hosts_tried=["h"])
        seen = []
        fleet = SimpleNamespace(choose=lambda spec, exclude: (seen.append(exclude) or ("h2", None)),
                                launched=lambda *a, **kw: None)
        ex = subprocess.TimeoutExpired(["ssh", "h"], 300)
        with patch.object(cl, "log"), patch.object(cl, "experiment"), \
                patch.object(cl, "host_cfg", return_value=dict(label="H", base="/b")):
            for _ in range(3):
                self.assertTrue(cl.handle_transient(j, fleet, ex))
        self.assertEqual((j["host"], j["status"], j["stage_idx"], j["transient"]), ("h2", "SYNC", cal, 0))
        self.assertEqual(seen, [["h"]])
        self.assertNotIn("transient_next", j)
        # stage_tag left over from the finished calibrate (never cleared) does not pin a READY route job
        j2 = job(spec=spec, status="READY", stage_tag="calibrate.a1", stage_idx=rt, hosts_tried=["h"])
        with patch.object(cl, "log"), patch.object(cl, "experiment"), \
                patch.object(cl, "host_cfg", return_value=dict(label="H", base="/b")):
            for _ in range(3):
                cl.handle_transient(j2, fleet, ex)
        self.assertEqual((j2["host"], j2["stage_idx"]), ("h2", cal))
        # a launched route (RUNNING) keeps backing off on its host
        j3 = job(spec=spec, status="RUNNING", stage_tag="route.a1", stage_idx=rt, hosts_tried=["h"])
        with patch.object(cl, "log"), patch.object(cl, "experiment"), \
                patch.object(cl, "host_cfg", return_value=dict(label="H", base="/b")):
            for _ in range(3):
                cl.handle_transient(j3, fleet, ex)
        self.assertEqual(j3["host"], "h")


class MemoryOffload(unittest.TestCase):
    """HBM group A 2026-10-14: a bench that never fits the artifact host's memory moves after the wait, chain restarts."""

    class Tight(Fleet):
        def fits(self, host, *a):
            return (host != "h"), "h MemAvailable 88 GB < 96+2"

    def _run(self, since):
        j = job(bench_par=True, status="RUNNING", stage_idx=1, bench_location=dict(host="h", run="/r", attempt=1),
                btrack={"bench_exact": dict(state="done", host="h", run="/r", tag="bench_exact.a1b1", n=1)},
                benches={"bench_exact": dict(ok=True)}, bwait="x", bwait_since=since)
        launched = []

        def launch(v, st, cmd):
            v["stage_tag"] = f"{st['key']}.a{v['attempt']}"
            launched.append((v["host"], st["key"]))
        off = dict(host="h2", run="/b/t-bench", attempt=1)
        with patch.object(cl, "launch_stage", launch), patch.object(cl, "offload_bench_location", return_value=off), \
                patch.object(cl, "vanished_bench_location", return_value=False), patch.object(cl, "log"), \
                patch.object(cl, "hosts_table", return_value=[dict(name="h", caps=[]), dict(name="h2", caps=[])]):
            cl.bench_track(j, self.Tight(), cl.stage_list(SPEC))
        return j, launched

    def test_waits_before_the_threshold(self):
        j, launched = self._run(cl.now_iso())
        self.assertEqual(launched, [])
        self.assertEqual(j["bench_location"]["host"], "h")

    def test_moves_after_the_threshold_and_restarts_the_chain(self):
        j, launched = self._run("2026-10-14T00:00:00-07:00")
        self.assertEqual(launched, [("h2", "bench_neg")])
        self.assertEqual(j["bench_location"]["host"], "h2")
        self.assertNotIn("bench_exact", j["benches"])
        self.assertNotIn("bwait_since", j)


if __name__ == "__main__":
    unittest.main()
