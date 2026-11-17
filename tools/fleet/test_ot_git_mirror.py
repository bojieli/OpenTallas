"""ot-git-mirror sync: a ref GitHub rejects twice at the same sha is skipped (logged once, listed in rejected.json); a moved ref is retried;
`fetch` runs on its own; the forward step respects its time budget."""
import importlib.machinery, importlib.util, io, os, pathlib, subprocess as S, sys, tempfile, unittest
from contextlib import redirect_stdout

P = str(pathlib.Path(__file__).with_name("ot-git-mirror"))
ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")


def sh(*a, cwd=None):
    return S.run(a, cwd=cwd, env=ENV, capture_output=True, text=True, check=True).stdout.strip()


class Fixture:
    def __init__(self):
        self.d = pathlib.Path(tempfile.mkdtemp())
        self.up = self.d / "up.git"
        sh("git", "init", "-q", "--bare", str(self.up))
        hook = self.up / "hooks" / "pre-receive"
        hook.write_text('#!/bin/bash\nwhile read o n r; do case "$r" in *bad*) echo "remote: error: File big.bin is 471.23 MB; this exceeds GitHub\'s file size limit of 100.00 MB" >&2; exit 1;; esac; done\n')
        hook.chmod(0o755)
        self.mirror = self.d / "mirror.git"
        os.environ["OT_GIT_MIRROR"] = str(self.mirror)
        os.environ["OT_GIT_UPSTREAM"] = str(self.up)
        ld = importlib.machinery.SourceFileLoader("omm_t", P)
        self.m = importlib.util.module_from_spec(importlib.util.spec_from_loader("omm_t", ld)); ld.exec_module(self.m)
        self.m.install()
        self.w = self.d / "w"
        sh("git", "init", "-q", str(self.w))
        (self.w / "f").write_text("1"); sh("git", "add", "f", cwd=self.w); sh("git", "commit", "-qm", "c1", cwd=self.w)
        sh("git", "push", "-q", str(self.mirror), "HEAD:refs/heads/main", cwd=self.w) if False else None
        S.run(["git", "-C", str(self.mirror), "fetch", "-q", str(self.w), "HEAD:refs/heads/claude/bad-1"], env=ENV, check=True)
        S.run(["git", "-C", str(self.mirror), "fetch", "-q", str(self.w), "HEAD:refs/heads/claude/good-1"], env=ENV, check=True)

    def sync(self, **kw):
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.m.sync(**kw)
        return buf.getvalue()


class MirrorSync(unittest.TestCase):
    def test_rejected_twice_is_skipped_then_retried_when_the_ref_moves(self):
        f = Fixture()
        o1 = f.sync(); o2 = f.sync(); o3 = f.sync()
        self.assertIn("claude/bad-1", o1)
        self.assertIn("SKIPPING claude/bad-1", o2)
        self.assertNotIn("bad-1", o3)                       # skipped: no push attempt, no log line
        self.assertIn("file size limit", f.m.load_rejected()["refs/heads/claude/bad-1"]["why"])
        self.assertEqual(S.run(["git", "-C", str(f.up), "rev-parse", "-q", "--verify", "refs/heads/claude/good-1"], capture_output=True).returncode, 0)
        (f.w / "f").write_text("2"); sh("git", "commit", "-qam", "c2", cwd=f.w)
        S.run(["git", "-C", str(f.mirror), "fetch", "-q", "--force", str(f.w), "HEAD:refs/heads/claude/bad-1"], env=ENV, check=True)
        self.assertIn("claude/bad-1", f.sync())             # new sha: tried again

    def test_fetch_only_does_not_forward(self):
        f = Fixture()
        f.sync(fetch_only=True)
        self.assertNotEqual(S.run(["git", "-C", str(f.up), "rev-parse", "-q", "--verify", "refs/heads/claude/good-1"], capture_output=True).returncode, 0)

    def test_budget_stops_the_per_ref_loop(self):
        f = Fixture(); f.m.BUDGET_S = -1
        self.assertNotIn("re-forward", f.sync().replace("budget", ""))


if __name__ == "__main__":
    unittest.main()
