"""Historical timeout metadata remains pinned, but elapsed time never kills or judges a bench."""
import datetime as dt
import unittest
from unittest.mock import patch

import closure_loop as cl


def spec(**b):
    bench = dict(name="long", cmd="true", expect="pass", **b)
    return dict(stages=dict(bench=[bench, dict(name="neg", cmd="false", expect="fail")], route=dict(cmd="true")))


class BenchTimeoutOverride(unittest.TestCase):
    def test_copied(self):
        st = cl.stage_list(spec(timeout_s=6 * 3600))
        self.assertEqual(st[0]["timeout_s"], 6 * 3600)
        self.assertIsNone(st[1]["timeout_s"])          # no historical override

    def test_elapsed_compile_is_observation_only(self):
        from types import SimpleNamespace
        started = (dt.datetime.now().astimezone() - dt.timedelta(hours=13)).isoformat()
        for extra in ({}, {"timeout_s": 43200}):
            for expect in ("pass", "fail"):
                st = cl.stage_list(spec(**extra))[0]
                st.update(expect=expect, fail_regex="MUTANT_DETECTED")
                v = dict(name="long", events=[], host="h", run="/r", stage_tag="t", status="RUNNING")
                quiet = SimpleNamespace(returncode=0, stdout="END\n")
                with patch.object(cl, "ssh", return_value=quiet) as ssh, patch.object(cl, "log"):
                    self.assertIsNone(cl.bench_timed_out(v, st, started))
                    self.assertEqual(v["status"], "RUNNING")
                    self.assertNotIn("benches", v)
                    self.assertTrue(v["quiet_output_reported"])
                    self.assertEqual(ssh.call_count, 1)
                    self.assertNotIn("kill", ssh.call_args.args[1])
                    cl.bench_timed_out(v, st, started)
                    self.assertEqual(ssh.call_count, 1)

    def test_growing_compile_is_preserved_without_verdict(self):
        from types import SimpleNamespace
        started = (dt.datetime.now().astimezone() - dt.timedelta(days=2)).isoformat()
        v = dict(name="long", events=[], host="h", run="/r", stage_tag="t", status="RUNNING")
        growing = SimpleNamespace(returncode=0, stdout="/r/object.o\nEND\n")
        with patch.object(cl, "ssh", return_value=growing) as ssh:
            self.assertIsNone(cl.bench_timed_out(v, cl.stage_list(spec(timeout_s=1))[0], started))
        self.assertEqual(v["status"], "RUNNING")
        self.assertNotIn("quiet_output_reported", v)
        self.assertNotIn("kill", ssh.call_args.args[1])

    def test_parallel_running_mutant_cannot_pass_by_elapsed_time(self):
        from types import SimpleNamespace
        stl = cl.stage_list(spec(timeout_s=1))
        stl[0].update(expect="fail", fail_regex="MUTANT_DETECTED")
        key = stl[0]["key"]
        started = (dt.datetime.now().astimezone() - dt.timedelta(days=2)).isoformat()
        e = dict(state="running", tag="t", host="h", run="/r", n=1, started=started)
        j = dict(name="long", bench_par=True, status="RUNNING", host="h", run="/r", events=[],
                 spec=spec(timeout_s=1), benches={}, btrack={key:e})
        with patch.object(cl, "poll_stage", return_value=("RUNNING", None)), \
                patch.object(cl, "ssh", return_value=SimpleNamespace(returncode=0, stdout="END\n")) as ssh, \
                patch.object(cl, "stop_main_for_bench") as stop, patch.object(cl, "bench_outcome") as outcome, \
                patch.object(cl, "log"):
            self.assertTrue(cl.bench_track(j, None, stl))
        self.assertEqual(j["status"], "RUNNING")
        self.assertEqual(e["state"], "running")
        self.assertFalse(j["benches"])
        stop.assert_not_called()
        outcome.assert_not_called()
        self.assertNotIn("kill", ssh.call_args.args[1])
        self.assertTrue(e["quiet_output_reported"])


if __name__ == "__main__":
    unittest.main()
