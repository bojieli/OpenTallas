"""WAVE-CONFIG 11-16: wait_job waits on a pid, a systemd unit or an ot-run unit, never on a command-line pattern."""
import os, subprocess, sys, unittest, unittest.mock
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wait_job as W  # noqa: E402


class Pid(unittest.TestCase):
    def test_waits_for_a_child_then_returns(self):
        p = subprocess.Popen(["sleep", "1.5"])
        self.assertEqual(W.wait_pid(p.pid, timeout=0.3, poll=0.1), W.EXIT_TIMEOUT)
        p.wait()                                                       # reaped: pid gone
        self.assertEqual(W.wait_pid(p.pid), W.EXIT_BAD)                # no such pid at the start is an error, not "ended"

    def test_zombie_counts_as_ended(self):
        p = subprocess.Popen(["true"])
        for _ in range(100):
            st = W.pid_start(p.pid)
            if st and st[1] == "Z":
                break
            import time; time.sleep(0.05)
        self.assertEqual(W.wait_pid(p.pid, timeout=5, poll=0.05), W.EXIT_ENDED)
        p.wait()

    def test_self_and_parent_are_refused(self):
        self.assertEqual(W.wait_pid(os.getpid()), W.EXIT_BAD)
        self.assertEqual(W.wait_pid(os.getppid()), W.EXIT_BAD)

    def test_reused_pid_counts_as_ended(self):
        p = subprocess.Popen(["sleep", "5"])
        real = W.pid_start
        seq = iter([real(p.pid), (real(p.pid)[0] + 1, "S")])
        W.pid_start = lambda pid: next(seq)
        try:
            self.assertEqual(W.wait_pid(p.pid, timeout=5, poll=0.01), W.EXIT_ENDED)
        finally:
            W.pid_start = real; p.kill(); p.wait()

    def test_a_cmdline_that_names_the_pattern_is_not_what_it_waits_on(self):
        # the old bug: `pgrep -f PATTERN` matched the waiter itself.  Here the waiter's own command line holds the name of the job, and it still returns.
        job = subprocess.Popen(["sleep", "0.5"])
        r = subprocess.run([sys.executable, "-I", str(Path(W.__file__)), "--pid", str(job.pid), "--timeout", "20", "--poll", "0.1", "sleep"], capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)          # stray argument "sleep" refused by argparse: patterns are not an input at all
        r = subprocess.run([sys.executable, "-I", str(Path(W.__file__)), "--pid", str(job.pid), "--timeout", "20", "--poll", "0.1"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        job.wait()


class Unit(unittest.TestCase):
    def seq(self, states):
        it = iter(states)
        return lambda unit, user, host: next(it)

    def run_wait(self, states, **kw):
        return W.wait_unit("u.scope", sleep=lambda s: None, state=self.seq(states), **kw)

    def test_active_then_inactive(self):
        self.assertEqual(self.run_wait([("loaded", "active"), ("loaded", "active"), ("loaded", "inactive")]), W.EXIT_ENDED)

    def test_not_found_at_start_is_an_error_unless_missing_ok(self):
        self.assertEqual(self.run_wait([("not-found", "inactive")]), W.EXIT_BAD)
        self.assertEqual(self.run_wait([("not-found", "inactive")], missing_ok=True), W.EXIT_ENDED)

    def test_scope_that_vanishes_after_running_is_ended(self):
        self.assertEqual(self.run_wait([("loaded", "active"), ("not-found", "inactive")]), W.EXIT_ENDED)

    def test_unreadable_is_never_ended(self):
        self.assertEqual(self.run_wait([None] * 5), W.EXIT_BLIND)
        self.assertEqual(self.run_wait([None, None, ("loaded", "active"), None, ("loaded", "inactive")]), W.EXIT_ENDED)

    def test_timeout(self):
        t = iter(range(0, 1000, 10))
        r = W.wait_unit("u", sleep=lambda s: None, clock=lambda: next(t), timeout=25, state=lambda *a: ("loaded", "active"))
        self.assertEqual(r, W.EXIT_TIMEOUT)

    def test_unit_state_parses_systemctl_and_ssh(self):
        calls = []

        def run(cmd, **kw):
            calls.append(cmd)
            return SimpleNamespace(returncode=0, stdout="LoadState=loaded\nActiveState=active\n")
        self.assertEqual(W.unit_state("x.scope", True, "epyc2", run=run), ("loaded", "active"))
        self.assertEqual(calls[0][:6], ["ssh", "-n", "-o", "BatchMode=yes", "-o", "ControlPath=none"])
        self.assertIn("systemctl --user show", calls[0][-1])
        self.assertIsNone(W.unit_state("x", run=lambda c, **k: SimpleNamespace(returncode=255, stdout="")))

    def test_cli_refuses_a_pattern_like_unit_and_ot_run_adds_scope(self):
        for bad in ("a b", "x;y", "-f", ""):
            r = subprocess.run([sys.executable, "-I", str(Path(W.__file__)), "--unit", bad], capture_output=True, text=True)
            self.assertEqual(r.returncode, 2, (bad, r.stderr))
        seen = []
        with unittest.mock.patch.object(W, "wait_unit", lambda unit, user, host, *a, **k: seen.append((unit, user, host)) or 0):
            W.main(["--ot-run-unit", "oth-ubuntu-1-2", "--host", "epyc2"])
        self.assertEqual(seen, [("oth-ubuntu-1-2.scope", True, "epyc2")])


if __name__ == "__main__":
    unittest.main()
