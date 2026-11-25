"""REPO-STATE-1 11-14: tools/queue_view.py, bin/post.sh and the coord-commit.sh replay path.
Run: python3 -I -m unittest discover -s ~/coord/tools/tests -p 'test_queue_view.py'   (git, bash, flock, bc needed)"""
import os, subprocess as S, sys, tempfile, threading, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
COORD_SRC = HERE.parent.parent
sys.path.insert(0, str(HERE.parent))
import queue_view as QV  # noqa: E402

Q = "lanes/COORD-REVIEW-QUEUE.md"


def run(*a, cwd=None, env=None, check=True):
    r = S.run(list(a), cwd=cwd, env=env, capture_output=True, text=True)
    if check and r.returncode:
        raise AssertionError(f"{a}: {r.returncode}\n{r.stdout}\n{r.stderr}")
    return r


class ViewTests(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / "lanes/posts").mkdir(parents=True)
        (self.d / "lanes/archive").mkdir(parents=True)

    def w(self, rel, text):
        (self.d / rel).write_text(text)

    def view(self):
        return (self.d / Q).read_text()

    def test_merge_sorted_dedup_archive_and_legacy(self):
        self.w(Q, "# head\n- 2026-11-14 10:00 PST STATE [A -> COORD] legacy direct\n")
        self.w("lanes/archive/COORD-REVIEW-QUEUE-20261024-20261111.md", "- 2026-11-10 01:00 PST DONE [B -> COORD] archived\n")
        self.w("lanes/posts/A.md", "- 2026-11-14 10:00 PST STATE [A -> COORD] legacy direct\n"
                                   "- 2026-11-14 12:00 PST RESULT [A -> COORD] a2\n  cont a2\n\n")
        self.w("lanes/posts/B.md", "- 2026-11-10 01:00 PST DONE [B -> COORD] archived\n"
                                   "- 2026-11-14 19:30 UTC STATE [B -> COORD] b-utc (11:30 PST)\n")
        self.assertEqual(QV.main(["--coord", str(self.d), "--check"]), 1)
        QV.main(["--coord", str(self.d), "--apply"])
        v = self.view().splitlines()
        self.assertEqual(v[:2], ["# head", "- 2026-11-14 10:00 PST STATE [A -> COORD] legacy direct"])
        self.assertEqual(v[2:], ["- 2026-11-14 19:30 UTC STATE [B -> COORD] b-utc (11:30 PST)",
                                 "- 2026-11-14 12:00 PST RESULT [A -> COORD] a2", "  cont a2"])
        before = self.view()
        QV.main(["--coord", str(self.d), "--apply"])        # idempotent
        self.assertEqual(self.view(), before)
        self.assertEqual(QV.main(["--coord", str(self.d), "--check"]), 0)

    def test_append_only_and_missing_newline(self):
        self.w(Q, "x\n- 2026-11-14 09:00 PST STATE [L -> COORD] direct without newline")
        self.w("lanes/posts/L.md", "- 2026-11-14 09:05 PST STATE [L -> COORD] new\n")
        QV.main(["--coord", str(self.d), "--apply"])
        self.assertTrue(self.view().startswith("x\n- 2026-11-14 09:00 PST STATE [L -> COORD] direct without newline\n"))
        self.assertTrue(self.view().endswith("- 2026-11-14 09:05 PST STATE [L -> COORD] new\n"))


@unittest.skipUnless(all(S.run(["which", x], capture_output=True).returncode == 0 for x in ("git", "flock", "bc")), "tools")
class CommitTests(unittest.TestCase):
    """bare origin + two clones; coord-commit.sh from this tree run with COORD_DIR"""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
                        GIT_COMMITTER_EMAIL="t@t", COORD_BRANCH="coord/state", COORD_COMMIT_TLOG=str(self.d / "tlog"))
        run("git", "init", "-q", "--bare", str(self.d / "origin.git"))
        seed = self.d / "seed"
        run("git", "init", "-q", "-b", "coord/state", str(seed))
        for rel in ("bin/coord-commit.sh", "bin/post.sh", "tools/queue_view.py"):
            (seed / rel).parent.mkdir(parents=True, exist_ok=True)
            (seed / rel).write_bytes((COORD_SRC / rel).read_bytes())
            os.chmod(seed / rel, 0o755)
        (seed / "lanes/posts").mkdir(parents=True); (seed / "autopilot").mkdir()
        (seed / Q).write_text("# head\n")
        (seed / "autopilot/SHARED.json").write_text("shared v0\n")
        (seed / ".gitattributes").write_text("lanes/*.md merge=union\nlanes/posts/*.md merge=union\n")
        run("git", "add", ".", cwd=seed, env=self.env)
        run("git", "commit", "-qm", "seed", cwd=seed, env=self.env)
        run("git", "remote", "add", "origin", str(self.d / "origin.git"), cwd=seed)
        run("git", "push", "-q", "origin", "coord/state", cwd=seed)
        for n in ("hub", "other"):
            run("git", "clone", "-q", "-b", "coord/state", str(self.d / "origin.git"), str(self.d / n), env=self.env)

    def cc(self, tree, *args, post=False):
        e = dict(self.env, COORD_DIR=str(self.d / tree))
        script = "bin/post.sh" if post else "bin/coord-commit.sh"
        return run("bash", str(self.d / tree / script), *args, cwd=self.d / tree, env=e, check=False)

    def origin_file(self, rel):
        return run("git", "--git-dir", str(self.d / "origin.git"), "show", f"coord/state:{rel}").stdout

    def test_post_updates_view_in_same_commit(self):
        r = self.cc("hub", "LANE-A", "STATE [LANE-A -> COORD] hello", post=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("STATE [LANE-A -> COORD] hello", self.origin_file("lanes/posts/LANE-A.md"))
        self.assertIn("STATE [LANE-A -> COORD] hello", self.origin_file(Q))

    def test_replay_when_merge_conflicts_on_other_file(self):
        # other clone edits SHARED.md in place and pushes; the hub has a conflicting committed in-place edit
        o, h = self.d / "other", self.d / "hub"
        (o / "autopilot/SHARED.json").write_text("shared other\n")
        self.assertEqual(self.cc("other", "o edit", "autopilot/SHARED.json").returncode, 0)
        (h / "autopilot/SHARED.json").write_text("shared hub\n")
        run("git", "commit", "-qam", "hub local edit", cwd=h, env=self.env)
        head_before = run("git", "rev-parse", "HEAD", cwd=h).stdout
        r = self.cc("hub", "LANE-B", "RESULT [LANE-B -> COORD] survives conflict", post=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("survives conflict", self.origin_file("lanes/posts/LANE-B.md"))
        self.assertIn("survives conflict", self.origin_file(Q))
        self.assertEqual(self.origin_file("autopilot/SHARED.json"), "shared other\n")   # others' file untouched
        self.assertIn("replayed", (self.d / "tlog").read_text())
        st = run("git", "status", "--porcelain", "--untracked-files=no", cwd=h).stdout
        self.assertEqual(st, "")                                               # shared worktree left clean
        self.assertNotEqual(run("git", "rev-parse", "HEAD", cwd=h).stdout, "")
        del head_before

    def test_parallel_posters_lose_nothing(self):
        n = 12
        def one(k):
            tree = "hub" if k % 2 else "other"
            self.cc(tree, f"P{k}", f"STATE [P{k} -> COORD] parallel {k}", post=True)
        ts = [threading.Thread(target=one, args=(k,)) for k in range(n)]
        [t.start() for t in ts]; [t.join() for t in ts]
        # posts committed from the other clone reach the view through the generator on the hub (timer)
        run("git", "pull", "-q", "--no-rebase", "origin", "coord/state", cwd=self.d / "hub", env=self.env)
        QV.main(["--coord", str(self.d / "hub"), "--apply"])
        self.assertEqual(self.cc("hub", "queue-view", Q).returncode, 0)
        v = self.origin_file(Q)
        for k in range(n):
            self.assertIn(f"parallel {k}", self.origin_file(f"lanes/posts/P{k}.md"))
            self.assertEqual(v.count(f"parallel {k}\n"), 1, k)


class UnstampedContinuation(unittest.TestCase):
    def test_unstamped_first_column_line_stays_in_its_post(self):
        d = Path(tempfile.mkdtemp()); (d / "lanes/posts").mkdir(parents=True); (d / "lanes/archive").mkdir(parents=True)
        (d / Q).write_text("- 2026-11-13 10:00 PST FAILED [X -> COORD] old\n/work/a.sh: line 3: syntax error\n")
        (d / "lanes/posts/X.md").write_text("- 2026-11-14 10:00 PST FAILED [X -> COORD] new\n"
                                           "/work/a.sh: line 3: syntax error\n | kit k1\n")
        self.assertEqual(QV.main(["--coord", str(d), "--apply"]), 0)
        v = (d / Q).read_text()
        self.assertTrue(v.endswith("- 2026-11-14 10:00 PST FAILED [X -> COORD] new\n/work/a.sh: line 3: syntax error\n | kit k1\n"), v)


if __name__ == "__main__":
    unittest.main()


class AutoDoneTests(unittest.TestCase):
    """QUEUE-DONE-1124: an automatic rc=0 DONE stays in the lane file; DIED / rc!=0 / hand-written posts reach the queue"""
    def test_auto_done_rc0_not_queued(self):
        d = Path(tempfile.mkdtemp())
        (d / "lanes/posts").mkdir(parents=True)
        (d / "lanes/archive").mkdir(parents=True)
        (d / Q).write_text("")
        (d / "lanes/posts/S81-ALLFIX-INT.md").write_text(
            "- 2026-11-24 16:56 PST DONE [S81-ALLFIX-INT] ot-run oth-ubuntu-1-2 on tolerant-swine: rc=0 after 414 s, ended 16:56:41, log x, cmd: y\n"
            "- 2026-11-24 16:57 PST DIED [S81-ALLFIX-INT] ot-run oth-ubuntu-3-4 on tolerant-swine: rc=1 after 9 s, ended 16:57:00, log x, cmd: y\n"
            "- 2026-11-24 16:58 PST DONE [S81-ALLFIX-INT] ot-push-main main@abc on tolerant-swine: rc=2 after 30 s, ended 16:58:00, log x, cmd: y\n"
            "- 2026-11-24 16:59 PST DONE [S81-ALLFIX-INT -> COORD] c8 rows landed, rc=0 after review\n")
        got = [l[0] for _t, _f, _i, l in QV.missing(str(d))]
        self.assertEqual(len(got), 3)
        self.assertFalse(any("oth-ubuntu-1-2" in g for g in got))
        self.assertTrue(any("DIED" in g for g in got) and any("rc=2" in g for g in got) and any("-> COORD" in g for g in got))
