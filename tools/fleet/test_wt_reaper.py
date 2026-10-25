"""wt-reaper (INFRA-REAPER 2026-10-25): removes only clean, pushed, idle, unreferenced, unprotected worktrees."""
import importlib.util
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("wt_reaper", Path(__file__).with_name("wt-reaper.py"))
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)


def run(*cmd, cwd=None):
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True)


def age(path, hours):
    t = time.time() - hours * 3600
    for d, dirs, files in os.walk(path):
        for n in dirs + files:
            os.utime(os.path.join(d, n), (t, t), follow_symlinks=False)
    os.utime(path, (t, t))


class Reaper(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: subprocess.run(["rm", "-rf", str(self.t)]))
        env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        os.environ.update(env)
        self.origin, self.repo, self.root = self.t / "origin.git", self.t / "repo", self.t / "scratch"
        self.root.mkdir()
        run("git", "init", "-q", "--bare", str(self.origin))
        run("git", "init", "-q", "-b", "main", str(self.repo))
        (self.repo / "a.py").write_text("x = 1\n")
        run("git", "-C", str(self.repo), "add", "a.py")
        run("git", "-C", str(self.repo), "commit", "-qm", "c1")
        run("git", "-C", str(self.repo), "remote", "add", "origin", str(self.origin))
        run("git", "-C", str(self.repo), "push", "-q", "origin", "main")
        run("git", "-C", str(self.repo), "fetch", "-q", "origin")
        self.procs = []
        self.addCleanup(lambda: [p.kill() for p in self.procs])

    def wt(self, name, branch, pushed=True, hours=5.0):
        p = self.root / name
        run("git", "-C", str(self.repo), "worktree", "add", "-q", "-b", branch, str(p), "main")
        if not pushed:
            (p / "b.py").write_text("y = 2\n")
            run("git", "-C", str(p), "add", "b.py")
            run("git", "-C", str(p), "commit", "-qm", "local")
        admin = self.repo / ".git" / "worktrees" / name
        age(p, hours)
        age(admin, hours)
        return p

    def reap(self, *extra):
        state = self.t / "state"
        R.PROTECT_PATHS = [str(self.repo)]
        R.main(["--roots", str(self.root), "--state", str(state), "--rescue-dir", str(self.t / "rescue"),
                "--no-sudo", *extra])
        rows = [l.split("\t") for l in (state / "last-run.tsv").read_text().splitlines()[1:]]
        return {Path(r[4]).name: (r[3], r[7]) for r in rows}

    def test_dry_run_removes_nothing(self):
        p = self.wt("clean", "b1")
        v = self.reap()
        self.assertEqual(v["clean"][0], "REMOVE")
        self.assertTrue(p.exists())

    def test_apply_matrix(self):
        clean = self.wt("clean", "b1")
        unpushed = self.wt("unpushed", "b2", pushed=False)
        recent = self.wt("recent", "b3", hours=0.5)
        prot = self.wt("root-merge-x", "b4")
        pyc = self.wt("pyc", "b5")
        (pyc / "__pycache__").mkdir()
        (pyc / "__pycache__" / "a.cpython-312.pyc").write_bytes(b"\0" * 10)
        age(pyc, 5)
        dirty = self.wt("dirty", "b6")
        (dirty / "a.py").write_text("x = 3\n")
        age(dirty, 5)
        busy = self.wt("busy", "b7")
        self.procs.append(subprocess.Popen(["sleep", "60"], cwd=str(busy)))
        argv = self.wt("argv", "b8")
        self.procs.append(subprocess.Popen(["python3", "-c", "import time; time.sleep(60)", str(argv) + "/run.sh"]))
        locked = self.wt("locked", "b9")
        run("git", "-C", str(self.repo), "worktree", "lock", str(locked))
        v = self.reap("--apply")
        self.assertEqual(v["clean"][0], "REMOVED")
        self.assertFalse(clean.exists())
        self.assertEqual(v["pyc"][0], "REMOVED_FORCE")
        self.assertFalse(pyc.exists())
        for name, path in (("unpushed", unpushed), ("recent", recent), ("root-merge-x", prot), ("dirty", dirty),
                           ("busy", busy), ("argv", argv), ("locked", locked)):
            self.assertEqual(v[name][0], "KEEP", (name, v[name]))
            self.assertTrue(path.exists(), name)
        self.assertIn("HEAD not in any origin branch", v["unpushed"][1])
        self.assertIn("modified <", v["recent"][1])
        self.assertIn("protected", v["root-merge-x"][1])
        self.assertIn("proc/docker path", v["busy"][1])
        self.assertIn("live text", v["argv"][1])
        self.assertIn("locked", v["locked"][1])
        log = (self.t / "state" / "removals.tsv").read_text()
        self.assertIn(str(clean), log)
        self.assertIn(str(pyc), log)
        listed = subprocess.run(["git", "-C", str(self.repo), "worktree", "list"], capture_output=True, text=True).stdout
        self.assertNotIn(str(clean), listed)
        self.assertIn(str(dirty), listed)

    def test_dirty_idle_day_gets_nonempty_rescue_patch(self):
        d = self.wt("old", "b10")
        (d / "a.py").write_text("x = 4\n")
        (d / "new.txt").write_text("hello\n")
        idx_before = (self.repo / ".git" / "worktrees" / "old" / "index").read_bytes()
        age(d, 30)
        age(self.repo / ".git" / "worktrees" / "old", 30)
        v = self.reap("--apply")
        self.assertEqual(v["old"][0], "DIRTY_IDLE")
        self.assertTrue(d.exists())
        patches = list((self.t / "rescue").glob("*.patch"))
        self.assertEqual(len(patches), 1)
        txt = patches[0].read_text()
        self.assertIn("x = 4", txt)
        self.assertIn("new.txt", txt)
        self.assertEqual((self.repo / ".git" / "worktrees" / "old" / "index").read_bytes(), idx_before)
        r = subprocess.run(["git", "-C", str(self.repo), "apply", "--check", str(patches[0])], capture_output=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_head_only_in_non_origin_remote_is_kept(self):
        other = self.t / "other.git"
        run("git", "init", "-q", "--bare", str(other))
        run("git", "-C", str(self.repo), "remote", "add", "gaps", str(other))
        p = self.wt("side", "b11", pushed=False)
        run("git", "-C", str(p), "push", "-q", "gaps", "b11")
        run("git", "-C", str(self.repo), "fetch", "-q", "gaps")
        age(p, 5)
        age(self.repo / ".git" / "worktrees" / "side", 5)
        v = self.reap("--apply")
        self.assertEqual(v["side"][0], "KEEP")
        self.assertTrue(p.exists())

    def test_main_worktree_and_hub_protected(self):
        self.assertTrue(R.protected(str(self.repo), "", str(self.repo / ".git"), ()))
        self.assertTrue(R.protected("/x/closed_archive/wt", "/nonexistent", "/r/.git", ()))
        self.assertTrue(R.protected("/x/merge-hub", "/nonexistent", "/r/.git", ()))


if __name__ == "__main__":
    unittest.main()
