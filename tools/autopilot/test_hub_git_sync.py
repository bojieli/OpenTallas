"""hub_git_sync.sh coord: merge-based hub checkout sync (10-25: the epyc1 hub sat at 08:29 for 86 min because a local
commit + uncommitted CODEX-LOG/HANDOFF lines made the ff-only pull fail silently) + the LOOP-GAPS banner.
    python3 -m pytest -q tools/autopilot/test_hub_git_sync.py"""
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "hub_git_sync.sh"
B = "coord/state"


class HubSync(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Path(self.tmp.name)
        self.run_(["git", "init", "--bare", "-q", str(self.r / "remote")])
        seed = self.r / "seed"
        self.run_(["git", "init", "-q", "-b", B, str(seed)])
        self.cfg(seed)
        (seed / "lanes").mkdir()
        (seed / "autopilot").mkdir()
        (seed / "HANDOFF.md").write_text("h1\nDIE-CI LATEST: old\n")
        (seed / "CODEX-LOG.md").write_text("c1\n")
        (seed / "lanes/X.md").write_text("x1\n")
        (seed / "BRIEFING.md").write_text("b1\n")
        (seed / "autopilot/resolved.tsv").write_text("r1\n")
        self.git(seed, "add", ".")
        self.git(seed, "commit", "-qm", "base")
        self.git(seed, "remote", "add", "origin", str(self.r / "remote"))
        self.git(seed, "push", "-q", "origin", B)
        for n in ("hub", "other"):
            self.run_(["git", "clone", "-q", "-b", B, str(self.r / "remote"), str(self.r / n)])
            self.cfg(self.r / n)
        self.hub, self.other = self.r / "hub", self.r / "other"

    def tearDown(self):
        self.tmp.cleanup()

    def run_(self, cmd, **kw):
        return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)

    def cfg(self, p):
        self.git(p, "config", "user.name", "T")
        self.git(p, "config", "user.email", "t@example.com")

    def git(self, p, *a):
        return self.run_(["git", "-C", str(p), *a]).stdout

    def append(self, p, rel, line):
        with open(p / rel, "a") as f:
            f.write(line + "\n")

    def remote_commit(self, rel, line):
        self.git(self.other, "pull", "-q", "--no-rebase", "origin", B)
        self.append(self.other, rel, line)
        self.git(self.other, "commit", "-qam", "other " + line)
        self.git(self.other, "push", "-q", "origin", B)

    def sync(self):
        env = dict(os.environ, HUB_SYNC_COORD=str(self.hub), HUB_SYNC_REPO=str(self.r / "none"))
        return subprocess.run(["bash", str(SCRIPT), "coord"], capture_output=True, text=True, env=env)

    def remote_file(self, rel):
        return self.git(self.hub, "show", f"origin/{B}:{rel}")

    def test_the_1025_stall_local_commit_plus_dirty_logs(self):
        # the 08:29 state: one local commit + uncommitted CODEX-LOG / HANDOFF lines, remote moved on the same files
        self.append(self.hub, "lanes/X.md", "hub lane line")
        self.git(self.hub, "commit", "-qam", "local lane commit")
        self.append(self.hub, "CODEX-LOG.md", "hub codex line")
        self.append(self.hub, "HANDOFF.md", "hub handoff line")
        self.remote_commit("CODEX-LOG.md", "remote codex line")
        self.remote_commit("HANDOFF.md", "remote handoff line")
        self.remote_commit("lanes/X.md", "remote lane line")
        r = self.sync()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.git(self.hub, "status", "--porcelain", "--untracked-files=no"), "")
        self.assertEqual(self.git(self.hub, "rev-parse", "HEAD"), self.git(self.hub, "rev-parse", f"origin/{B}"))
        for rel, lines in (("CODEX-LOG.md", ["c1", "hub codex line", "remote codex line"]),
                           ("HANDOFF.md", ["h1", "hub handoff line", "remote handoff line"]),
                           ("lanes/X.md", ["x1", "hub lane line", "remote lane line"])):
            got = self.remote_file(rel).splitlines()
            for line in lines:
                self.assertEqual(got.count(line), 1, (rel, got))
            self.assertFalse([l for l in got if l.startswith(("<<<<<<<", "=======", ">>>>>>>"))], got)
        self.assertTrue((self.hub / "autopilot/HUB-SYNC-OK").is_file())
        self.assertFalse((self.hub / "autopilot/HUB-SYNC-FAILED").exists())

    def test_clean_hub_fast_forwards(self):
        self.remote_commit("lanes/X.md", "x2")
        r = self.sync()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("x2", (self.hub / "lanes/X.md").read_text())

    def test_die_ci_latest_replaced_once(self):
        t = (self.hub / "HANDOFF.md").read_text().replace("DIE-CI LATEST: old", "DIE-CI LATEST: new")
        (self.hub / "HANDOFF.md").write_text(t)
        self.remote_commit("HANDOFF.md", "remote line")
        r = self.sync()
        self.assertEqual(r.returncode, 0, r.stderr)
        h = self.remote_file("HANDOFF.md")
        self.assertEqual([l for l in h.splitlines() if "DIE-CI LATEST" in l], ["DIE-CI LATEST: new"])
        self.assertIn("remote line", h)

    def test_non_log_edit_fails_loud_and_is_kept(self):
        self.append(self.hub, "BRIEFING.md", "local briefing edit")
        self.remote_commit("lanes/X.md", "x2")
        r = self.sync()
        self.assertNotEqual(r.returncode, 0)
        f = (self.hub / "autopilot/HUB-SYNC-FAILED").read_text()
        self.assertTrue(f.startswith("since "), f)
        self.assertIn("BRIEFING.md", f)
        self.assertIn("local briefing edit", (self.hub / "BRIEFING.md").read_text())   # nothing discarded
        first = f.splitlines()[0]
        time.sleep(1.1)
        self.sync()
        self.assertEqual((self.hub / "autopilot/HUB-SYNC-FAILED").read_text().splitlines()[0], first)  # first time kept
        # fixed by hand -> next sync clears the flag
        self.git(self.hub, "checkout", "--", "BRIEFING.md")
        r = self.sync()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse((self.hub / "autopilot/HUB-SYNC-FAILED").exists())

    def test_conflict_outside_logs_aborts_merge(self):
        self.append(self.hub, "BRIEFING.md", "hub b")
        self.git(self.hub, "commit", "-qam", "hub briefing")
        self.remote_commit("BRIEFING.md", "remote b")
        r = self.sync()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("BRIEFING.md", (self.hub / "autopilot/HUB-SYNC-FAILED").read_text())
        self.assertFalse((self.hub / ".git/MERGE_HEAD").exists())
        self.assertEqual(self.git(self.hub, "status", "--porcelain", "--untracked-files=no"), "")


class Banner(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["AP_DIR"] = self.tmp.name
        sys.path.insert(0, str(HERE))
        import autopilot
        import importlib
        self.ap = importlib.reload(autopilot)
        self.d = Path(self.tmp.name)

    def tearDown(self):
        os.environ.pop("AP_DIR", None)
        self.tmp.cleanup()

    def test_banner(self):
        now = time.time()
        self.assertEqual(self.ap.hub_sync_banner(now), "")
        (self.d / "HUB-SYNC-OK").write_text("2026-10-25 10:00 PDT abc\n")
        self.assertEqual(self.ap.hub_sync_banner(now), "")
        os.utime(self.d / "HUB-SYNC-OK", (now - 3600, now - 3600))
        b = self.ap.hub_sync_banner(now)
        self.assertTrue(b.startswith("HUB-SYNC-FAILED since 2026-10-25 10:00 PDT: no successful"), b)
        (self.d / "HUB-SYNC-FAILED").write_text("since 2026-10-25 08:29 PDT\nnon-log local edits: X (last attempt ...)\n")
        b = self.ap.hub_sync_banner(now)
        self.assertEqual(b.splitlines(), ["HUB-SYNC-FAILED since 2026-10-25 08:29 PDT: non-log local edits: X (last attempt ...)"])


if __name__ == "__main__":
    unittest.main()
