"""ot-run --cancel-dir (COORD 11-11 15:5x): end the autopilot's record of a job whose ot-run client is already dead, through the
signals.log line autopilot.signals_cancel() accepts (instead of the 3 h ORPHAN timer)."""
import importlib.machinery
import importlib.util
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
AP = HERE.parent / "autopilot"
KIT = "/srv/opentallas-scratch2/claude/kw43-wave-1109/runs/hbm/kit-wave/hbm/hcut1111/items/q_x/attempt_2/gen/q_x"


def load_otrun(log):
    loader = importlib.machinery.SourceFileLoader("ot_run_cd", str(HERE / "ot-run"))
    m = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
    loader.exec_module(m)
    m.SIGNAL_LOG = log
    return m


def load_autopilot(log):
    os.environ["AP_OT_RUN_SIGNALS"] = log
    sys.path.insert(0, str(AP))
    spec = importlib.util.spec_from_file_location("autopilot_cd", str(AP / "autopilot.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class CancelDir(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp(prefix="cdir")
        self.log = os.path.join(self.t, "signals.log")
        self.m = load_otrun(self.log)
        self.procs = []

    def tearDown(self):
        for p in self.procs:
            p.kill()
            p.wait()

    def test_writes_the_line_the_autopilot_accepts(self):
        self.assertEqual(self.m.cancel_dir(f"epyc8:{KIT}", "KW-FIX-45 pilot relaunch"), 0)
        line = open(self.log).read().strip()
        self.assertIn("ot-run --cancel", line)
        self.assertIn(f" dir {KIT}: ", line)
        ap = load_autopilot(self.log)
        got = ap.signals_cancel({"path": KIT, "started": time.time() - 3600})
        self.assertIsNotNone(got, line)
        self.assertIn("signal 15 from", got)

    def test_job_started_after_the_record_is_not_cancelled(self):
        self.m.cancel_dir(KIT, "old")
        ap = load_autopilot(self.log)
        self.assertIsNone(ap.signals_cancel({"path": KIT, "started": time.time() + 3600}))   # a later attempt

    def test_other_kit_paths_are_not_cancelled(self):
        self.m.cancel_dir(KIT, "x")
        ap = load_autopilot(self.log)
        self.assertIsNone(ap.signals_cancel({"path": KIT + "_b", "started": time.time() - 3600}))
        self.assertIsNone(ap.signals_cancel({"path": KIT.replace("attempt_2", "attempt_3"), "started": time.time() - 3600}))

    def test_refuses_while_a_live_client_has_that_dir(self):
        bindir = os.path.join(self.t, "bin")
        os.makedirs(bindir)
        fake = os.path.join(bindir, "ot-run")
        with open(fake, "w") as f:
            f.write("#!/usr/bin/env python3\nimport time\ntime.sleep(30)\n")
        os.chmod(fake, 0o755)
        self.procs.append(subprocess.Popen([fake, "--mem", "1", "--dir", KIT, "--", "true"]))
        time.sleep(0.5)
        self.assertEqual(self.m.cancel_dir(KIT, "x"), 2)
        self.assertFalse(os.path.exists(self.log))                       # nothing written

    def test_a_multiline_parent_command_still_makes_one_accepted_line(self):
        # found live 16:07: the invoking ssh command held a heredoc, the record was split over two lines and signals_cancel() never matched
        self.m.sender = lambda pid: f"pid {pid} (bash -c python3 - <<EOF\nimport json\nprint('x')\nEOF\nmore; parent 1 (sshd))"
        self.assertEqual(self.m.cancel_dir(KIT, "multi-line parent"), 0)
        lines = open(self.log).read().splitlines()
        self.assertEqual(len(lines), 1, lines)
        ap = load_autopilot(self.log)
        self.assertIsNotNone(ap.signals_cancel({"path": KIT, "started": time.time() - 3600}))

    def test_relative_path_is_refused(self):
        self.assertEqual(self.m.cancel_dir("q_x/attempt_2", "x"), 2)
        self.assertFalse(os.path.exists(self.log))

    def test_cli_entry(self):
        env = dict(os.environ, HOME=self.t)
        r = subprocess.run([sys.executable, "-I", str(HERE / "ot-run"), "--cancel-dir", KIT, "--reason", "cli test"],
                           capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("wrote the cancel record", r.stdout)
        self.assertIn(f" dir {KIT}: cli test", open(os.path.join(self.t, ".local/state/ot-run/signals.log")).read())


if __name__ == "__main__":
    unittest.main()
