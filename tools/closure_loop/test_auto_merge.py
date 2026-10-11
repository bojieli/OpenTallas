"""AUTO-MERGE (owner 2026-10-10): CLOSED + benches as expected + claude/* source -> verified commit + record merged to main."""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("CL_STATE", tempfile.mkdtemp(prefix="automerge_"))
import closure_loop as cl  # noqa: E402


def run(*a, cwd):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *a], cwd=cwd, check=True,
                          capture_output=True, text=True).stdout.strip()


class AutoMerge(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.origin, self.work, self.repo = self.t / "origin.git", self.t / "work", self.t / "repo"
        run("init", "-q", "--bare", "-b", "main", str(self.origin), cwd=self.t)
        run("clone", "-q", str(self.origin), str(self.work), cwd=self.t)
        w = self.work
        (w / "rtl").mkdir(); (w / "rtl/a.sv").write_text("module a; endmodule\n")
        (w / "tools/closure_loop").mkdir(parents=True); (w / "tools/closure_loop/x").write_text("x\n")
        run("add", "-A", cwd=w); run("commit", "-qm", "base", cwd=w); run("push", "-q", "origin", "HEAD:main", cwd=w)
        run("checkout", "-qb", "claude/feat", cwd=w)
        (w / "rtl/a.sv").write_text("module a; wire v; endmodule\n"); run("commit", "-qam", "verified", cwd=w)
        self.verified = run("rev-parse", "HEAD", cwd=w)
        (w / "rtl/b.sv").write_text("module b; endmodule\n"); run("add", "rtl/b.sv", cwd=w); run("commit", "-qm", "later", cwd=w)
        (w / "results/closure_loop/job1").mkdir(parents=True)
        (w / "results/closure_loop/job1/verdict.json").write_text("{}\n")
        run("add", "results", cwd=w); run("commit", "-qm", "record", cwd=w)
        self.record = run("rev-parse", "HEAD", cwd=w)
        run("push", "-q", "origin", "claude/feat", cwd=w)
        run("clone", "-q", str(self.origin), str(self.repo), cwd=self.t)
        self.state = self.t / "state"; (self.state / "git").mkdir(parents=True)
        (self.state / "main_publish_owner.json").write_text(json.dumps({"automatic_main_publish": False, "auto_merge_guarded": True}))
        for p in (patch.object(cl, "REPO", self.repo), patch.object(cl, "STATE", self.state),
                  patch.object(cl, "AUTO_MERGE_PENDING", self.t / "PENDING.md"), patch.object(cl, "log")):
            p.start(); self.addCleanup(p.stop)

    def job(self, **kw):
        j = dict(name="job1", commit_full=self.verified, spec={"block": "a", "source": {"branch": "claude/feat"}},
                 benches={"pos": {"expect": "pass", "ok": True}, "mut": {"expect": "fail", "ok": True}})
        j.update(kw)
        return j

    def main_tree(self):
        run("fetch", "-q", "origin", cwd=self.repo)
        return run("ls-tree", "-r", "--name-only", "origin/main", cwd=self.repo).split()

    def test_merges_verified_commit_and_record_only(self):
        st = cl.auto_merge_closure(self.job(), {"branch_commit": self.record, "record_branch": "claude/feat"},
                                   ["results/closure_loop/job1"])
        self.assertTrue(st.startswith("AUTO-MERGED"), st)
        files = self.main_tree()
        self.assertIn("results/closure_loop/job1/verdict.json", files)
        self.assertNotIn("rtl/b.sv", files)                      # the unverified later commit stays off main
        self.assertIn("wire v", run("show", "origin/main:rtl/a.sv", cwd=self.repo))

    def test_guards(self):
        out = {"branch_commit": self.record}
        bad_bench = self.job(benches={"pos": {"expect": "pass", "ok": False}})
        self.assertIn("benches not as expected", cl.auto_merge_closure(bad_bench, out, ["results/closure_loop/job1"]))
        codex = self.job(spec={"block": "a", "source": {"branch": "codex/x"}})
        self.assertIn("not claude/*", cl.auto_merge_closure(codex, out, ["results/closure_loop/job1"]))
        held = self.job(spec={"block": "a", "source": {"branch": "claude/feat"}, "hold_merge": "svc scoreboard"})
        self.assertIn("opts out", cl.auto_merge_closure(held, out, ["results/closure_loop/job1"]))
        self.assertIn("no loop benches", cl.auto_merge_closure(self.job(benches={}), out, ["results/closure_loop/job1"]))
        self.assertNotIn("results/closure_loop/job1/verdict.json", self.main_tree())
        self.assertEqual(len((self.t / "PENDING.md").read_text().splitlines()), 4)

    def test_conflict_is_queued_not_forced(self):
        w = self.work
        run("checkout", "-q", "main", cwd=w); run("pull", "-q", "origin", "main", cwd=w)
        (w / "rtl/a.sv").write_text("module a; wire other; endmodule\n"); run("commit", "-qam", "main moved", cwd=w)
        run("push", "-q", "origin", "HEAD:main", cwd=w)
        st = cl.auto_merge_closure(self.job(), {"branch_commit": self.record}, ["results/closure_loop/job1"])
        self.assertTrue(st.startswith("AUTO-MERGE CONFLICT"), st)
        self.assertIn("other", run("show", "origin/main:rtl/a.sv", cwd=self.repo) if self.main_tree() else "")
        self.assertIn("CONFLICT", (self.t / "PENDING.md").read_text())

    def test_policy_hold_prefix(self):
        (self.state / "main_publish_owner.json").write_text(json.dumps({"auto_merge_guarded": True, "auto_merge_hold_prefixes": ["a"]}))
        self.assertIn("held by policy prefix", cl.auto_merge_closure(self.job(), {"branch_commit": self.record}, ["results/closure_loop/job1"]))

    def test_policy_off(self):
        (self.state / "main_publish_owner.json").write_text(json.dumps({"automatic_main_publish": False}))
        self.assertIn("policy off", cl.auto_merge_closure(self.job(), {"branch_commit": self.record}, ["results/closure_loop/job1"]))


if __name__ == "__main__":
    unittest.main()
