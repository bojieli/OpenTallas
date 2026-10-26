"""ot-heavy v17 exit report (TOKc-ADM 2026-10-22): an earlyoom kill of a job's process is reported as EARLYOOM, a scope
memcg OOM as MEMCG-OOM, never a bare 143 / make error 2."""
import contextlib, importlib.machinery, importlib.util, io, os, pathlib, subprocess, tempfile, unittest
from unittest.mock import patch

HERE = pathlib.Path(__file__).resolve().parent
loader = importlib.machinery.SourceFileLoader("otr_exit", str(HERE / "ot-heavy-reconcile"))
spec = importlib.util.spec_from_loader("otr_exit", loader)
R = importlib.util.module_from_spec(spec)
loader.exec_module(R)

EO = [
    "2026-10-22T14:15:44-07:00 ot-epyc5 earlyoom[1366863]: mem avail: 32268 of 1093354 MiB ( 2.95%), swap free: 13223 of 139263 MiB ( 9.50%)",
    '2026-10-22T14:15:44-07:00 ot-epyc5 earlyoom[1366863]: sending SIGTERM to process 2234736 uid 1000 "cc1plus": oom_score 988, '
    'oom_score_adj 0, VmRSS 43995 MiB, cmdline "/usr/libexec/gcc/x86_64-linux-gnu/15/cc1plus -quiet -I ."',
    '2026-10-22T14:15:54-07:00 ot-epyc5 earlyoom[1366863]: sending SIGTERM to process 2234736 uid 1000 "cc1plus": oom_score 988, '
    'oom_score_adj 0, VmRSS 43995 MiB, cmdline "x"',
    '2026-10-22T14:16:02-07:00 ot-epyc5 earlyoom[1366863]: sending SIGTERM to process 999 uid 1000 "cc1plus": oom_score 988, '
    'oom_score_adj 0, VmRSS 43578 MiB, cmdline "x"',
]


class ExitReport(unittest.TestCase):
    def run_report(self, pids, cg=""):
        with tempfile.TemporaryDirectory() as d:
            pf = os.path.join(d, "pids")
            open(pf, "w").write("\n".join(map(str, pids)) + "\n")
            out = io.StringIO()
            with patch.object(R, "journal", return_value=EO), patch.object(R, "D", d), contextlib.redirect_stdout(out):
                R.exit_report("oth-ubuntu-2136627-1792690948", "1792690948", "2", pf, cg)
            return out.getvalue()

    def test_ep5_1415_cc1plus_kill_is_earlyoom(self):
        text = self.run_report([2136627, 2234736])
        self.assertIn("EARLYOOM", text)
        self.assertIn("pid 2234736 cc1plus VmRSS 43.0 GiB", text)
        self.assertIn("mem avail 2.95 %", text)
        self.assertNotIn("pid 999", text)
        self.assertEqual(text.count("EARLYOOM"), 1)       # repeated SIGTERMs to one pid: one line                 # another scope's kill is not this job's

    def test_no_kill_of_this_scope_reports_nothing(self):
        self.assertEqual(self.run_report([1, 2, 3]), "")

    def test_memcg_oom(self):
        with tempfile.TemporaryDirectory() as cg:
            open(f"{cg}/memory.events", "w").write("low 0\nhigh 0\nmax 4\noom 1\noom_kill 1\n")
            open(f"{cg}/memory.max", "w").write("8589934592\n")
            open(f"{cg}/memory.peak", "w").write("8589934592\n")
            self.assertIn("MEMCG-OOM", self.run_report([5], cg))


class Wrapper(unittest.TestCase):
    W = str(HERE / "ot-heavy-exit")

    def test_status_and_stdin_pass_through(self):
        r = subprocess.run([self.W, "oth-test-x", "bash", "-c", "cat; exit 3"], input="hi\n", capture_output=True, text=True,
                           env=dict(os.environ), timeout=60)
        self.assertEqual((r.returncode, r.stdout), (3, "hi\n"))
        self.assertEqual(subprocess.run([self.W, "oth-test-y", "true"], timeout=60).returncode, 0)

    def test_term_is_forwarded(self):
        p = subprocess.Popen([self.W, "oth-test-z", "sleep", "60"])
        import time
        time.sleep(1)
        p.terminate()
        self.assertEqual(p.wait(timeout=20), 143)


if __name__ == "__main__":
    unittest.main()
