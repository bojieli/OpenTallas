"""DIECI_WD_1101 (COORD 11-01 19:0x): die_ci_cron.sh stops its own run after the max runtime, on the 2-h no-write
watchdog, and when a newer nightly starts.  Runs the real script against a throwaway HOME: a git repo as the hub, fake
ssh (runs the command locally), fake ot-run (a job that starts a scope and then hangs), fake systemctl/docker."""
import os
import pathlib
import subprocess
import tempfile
import time
import unittest

HERE = pathlib.Path(__file__).resolve().parent
CRON = HERE / "die_ci_cron.sh"

FAKE_DIE_CI = '''import sys
a = sys.argv[1:]
if a and a[0] == "job-mem":
    print(8)
elif a and a[0] == "stage-views":
    pass
def resolve_plans(repo, extra=None):
    return {"d1": None}
'''
FAKE_OTRUN = '''#!/bin/bash
# fake ot-run: --pick -> localhost; a job -> scope line, record pid, then hang without writing
case " $* " in *" --pick "*) echo localhost; exit 0;; esac
echo "ot-run: admitted on localhost unit oth-fake-$$.scope"
echo $$ >> "$HOME/otrun_jobs"
exec sleep 600
'''
FAKE_SSH = '''#!/bin/bash
while [ $# -gt 0 ]; do case "$1" in -o) shift 2;; -*) shift;; *) break;; esac; done
shift   # host
exec bash -c "$*"
'''
FAKE_SYSTEMCTL = '''#!/bin/bash
echo "$*" >> "$HOME/systemctl.log"
'''


class CronWatchdog(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(prefix="dieci-cron-")
        self.addCleanup(t.cleanup)
        self.home = pathlib.Path(t.name)
        hub = self.home / "OpenTallas"
        (hub / "tools/die_plan").mkdir(parents=True)
        (hub / "tools/die_plan/die_ci.py").write_text(FAKE_DIE_CI)
        (hub / "tools/die_plan/die_sta.py").write_text("")
        g = ["git", "-C", str(hub)]
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
                   GIT_COMMITTER_EMAIL="t@t")
        subprocess.run(g + ["init", "-q", "-b", "main"], check=True, env=env)
        subprocess.run(g + ["add", "-A"], check=True, env=env)
        subprocess.run(g + ["commit", "-qm", "x"], check=True, env=env)
        subprocess.run(g + ["remote", "add", "origin", str(hub)], check=True, env=env)
        b = self.home / ".local/bin"
        b.mkdir(parents=True)
        for n, txt in (("ot-run", FAKE_OTRUN), ("ssh", FAKE_SSH), ("systemctl", FAKE_SYSTEMCTL),
                       ("docker", "#!/bin/bash\nexit 1\n")):
            (b / n).write_text(txt)
            (b / n).chmod(0o755)
        self.env = dict(env, HOME=str(self.home), PATH=f"{b}:{os.environ['PATH']}",
                        DIE_CI_LOCAL_ROOT=str(self.home / "lr"), DIE_CI_RUN_ROOT=str(self.home / "r"),
                        DIE_CI_RESULTS_WT=str(self.home / "resw"), DIE_CI_HANDOFF=str(self.home / "HANDOFF.md"),
                        DIE_CI_TOOLS=str(hub / "tools/die_plan"), OT_HUB_NAME="intel2", DIE_CI_POLL_S="1")
        self.addCleanup(self.kill_jobs)

    def kill_jobs(self):
        f = self.home / "otrun_jobs"
        for p in (f.read_text().split() if f.exists() else []):
            try:
                os.kill(int(p), 9)
            except (OSError, ValueError):
                pass

    def start(self, **env):
        out = open(self.home / f"out{time.time_ns()}.log", "w")
        self.addCleanup(out.close)
        return subprocess.Popen(["bash", str(CRON), "nightly"], env=dict(self.env, **env), stdout=out,
                                stderr=subprocess.STDOUT, start_new_session=True)

    def wait_for(self, pred, t=60):
        end = time.time() + t
        while time.time() < end:
            if pred():
                return True
            time.sleep(0.3)
        return False

    def cron_log(self):
        p = self.home / "lr/logs/cron.log"
        return p.read_text() if p.exists() else ""

    def job_dead(self):
        f = self.home / "otrun_jobs"
        pids = f.read_text().split() if f.exists() else []
        return bool(pids) and not any(pathlib.Path(f"/proc/{p}").exists() for p in pids)

    def test_watchdog_stops_a_silent_run_and_its_scope(self):
        pr = self.start(DIE_CI_IDLE_S="3", DIE_CI_MAX_S="600")
        self.assertEqual(pr.wait(timeout=90), 143, self.cron_log())
        log = self.cron_log()
        self.assertIn("STOPPED (watchdog: no file under", log)
        self.assertIn("NOT COMPLETED", log)
        self.assertRegex((self.home / "systemctl.log").read_text(), r"--user stop oth-fake-\d+\.scope")
        self.assertTrue(self.wait_for(self.job_dead, 20), "ot-run client still alive")

    def test_max_runtime_stops_the_run(self):
        pr = self.start(DIE_CI_IDLE_S="600", DIE_CI_MAX_S="4")
        self.assertEqual(pr.wait(timeout=90), 143, self.cron_log())
        self.assertIn("STOPPED (max runtime", self.cron_log())

    def test_newer_nightly_preempts_the_older_run(self):
        old = self.start(DIE_CI_IDLE_S="600", DIE_CI_MAX_S="600")
        self.assertTrue(self.wait_for(lambda: (self.home / "otrun_jobs").exists(), 60), self.cron_log())
        new = self.start(DIE_CI_IDLE_S="600", DIE_CI_MAX_S="6")
        self.assertEqual(old.wait(timeout=90), 143, self.cron_log())
        self.assertIn("a newer nightly starts; stopping the previous nightly run", self.cron_log())
        self.assertIn("STOPPED (SIGTERM", self.cron_log())
        new.wait(timeout=120)
        self.assertGreaterEqual(self.cron_log().count("per-die jobs on localhost"), 2, self.cron_log())


if __name__ == "__main__":
    unittest.main()
