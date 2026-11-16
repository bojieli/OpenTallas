"""ot-git-mirror + ot-lane-clone: lanes clone the mirror, push claude/* only, the mirror forwards to GitHub (FABLE-FLOW class 8)"""
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).parent
MIRROR = str(HERE / "ot-git-mirror")
CLONE = str(HERE / "ot-lane-clone")
G = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "init.defaultBranch=main"]


def sh(*a, cwd=None, check=True):
    p = subprocess.run(a, cwd=cwd, capture_output=True, text=True, timeout=300)
    if check and p.returncode:
        raise AssertionError(f"{a}: {p.stdout}{p.stderr}")
    return p


class LaneMirror(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        d = self.d = pathlib.Path(self._td.name)
        self.gh = d / "github.git"
        sh(*G, "init", "-q", "--bare", str(self.gh))
        seed = d / "seed"
        sh(*G, "clone", "-q", str(self.gh), str(seed))
        (seed / "a.txt").write_text("1\n")
        sh(*G, "add", "a.txt", cwd=seed); sh(*G, "commit", "-qm", "base", cwd=seed); sh(*G, "push", "-q", "origin", "main", cwd=seed)
        self.seed = seed
        self.m = d / "mirror.git"
        self.env = dict(os.environ, OT_GIT_MIRROR=str(self.m), OT_GIT_UPSTREAM=str(self.gh), OT_LANE_MIRROR=str(self.m),
                        GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        self.run_(MIRROR, "install"); self.run_(MIRROR, "sync")

    def tearDown(self):
        self._td.cleanup()

    def run_(self, tool, *a, ok=True):
        p = subprocess.run([sys.executable, "-I", tool, *a], env=self.env, capture_output=True, text=True, timeout=300)
        if ok:
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        return p

    def gh_ref(self, ref):
        return sh("git", "rev-parse", "-q", "--verify", ref, cwd=self.gh, check=False).stdout.strip()

    def test_clone_push_claude_branch_reaches_github_main_and_other_remotes_refused(self):
        c = self.d / "lane"
        self.run_(CLONE, str(c), "-b", "claude/x-1115")
        self.assertEqual(sh("git", "remote", "get-url", "origin", cwd=c).stdout.strip(), str(self.m))
        (c / "a.txt").write_text("2\n")
        sh("git", "commit", "-qam", "x", cwd=c, check=True)
        p = subprocess.run(["git", "push", "origin", "claude/x-1115"], cwd=c, env=self.env, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("forwarded claude/x-1115", p.stderr)
        self.assertEqual(self.gh_ref("refs/heads/claude/x-1115"), sh("git", "rev-parse", "HEAD", cwd=c).stdout.strip())
        p = subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=c, env=self.env, capture_output=True, text=True)
        self.assertNotEqual(p.returncode, 0)                                  # the clone hook refuses main
        p = subprocess.run(["git", "push", "--no-verify", "origin", "HEAD:main"], cwd=c, env=self.env, capture_output=True, text=True)
        self.assertNotEqual(p.returncode, 0)                                  # and the mirror refuses it too
        self.assertIn("claude/* branches only", p.stderr)
        p = subprocess.run(["git", "push", str(self.gh), "HEAD:refs/heads/claude/y"], cwd=c, env=self.env, capture_output=True, text=True)
        self.assertNotEqual(p.returncode, 0)                                  # pushes go to the mirror only
        self.assertEqual(self.gh_ref("refs/heads/claude/y"), "")

    def _seed_dirs(self):
        for dname in ("physical", "results", "tools"):
            (self.seed / dname).mkdir(exist_ok=True)
            (self.seed / dname / "f.txt").write_text(dname + "\n")
        sh(*G, "add", "-A", cwd=self.seed); sh(*G, "commit", "-qm", "dirs", cwd=self.seed); sh(*G, "push", "-q", "origin", "main", cwd=self.seed)
        self.run_(MIRROR, "sync")

    def test_clone_is_light_by_default_and_with_brings_dirs_back(self):
        self._seed_dirs()
        c = self.d / "light"
        self.run_(CLONE, str(c), "-b", "claude/l-1115")
        self.assertTrue((c / "tools" / "f.txt").exists())
        self.assertFalse((c / "physical").exists())
        self.assertFalse((c / "results").exists())
        w = self.d / "withphys"
        self.run_(CLONE, str(w), "-b", "claude/w-1115", "--with", "physical")
        self.assertTrue((w / "physical" / "f.txt").exists())
        self.assertFalse((w / "results").exists())
        f = self.d / "full"
        self.run_(CLONE, str(f), "-b", "claude/f-1115", "--full")
        self.assertTrue((f / "results" / "f.txt").exists())

    def test_shared_store_is_used_as_reference(self):
        self._seed_dirs()
        sh_ = self.d / "shared.git"
        self.env["OT_LANE_SHARED"] = str(sh_)
        self.run_(CLONE, "--refresh-shared")
        self.assertTrue(sh_.is_dir())
        c = self.d / "ref"
        self.run_(CLONE, str(c), "-b", "claude/r-1115")
        alt = (c / ".git" / "objects" / "info" / "alternates").read_text()
        self.assertIn(str(sh_), alt)

    def test_sync_fetches_main_and_reforwards_a_failed_forward(self):
        (self.seed / "a.txt").write_text("3\n")
        sh(*G, "commit", "-qam", "main2", cwd=self.seed); sh(*G, "push", "-q", "origin", "main", cwd=self.seed)
        c = self.d / "lane"
        self.run_(CLONE, str(c), "-b", "claude/z-1115")
        (c / "a.txt").write_text("4\n")
        sh("git", "commit", "-qam", "z", cwd=c)
        (self.m / "hooks/post-receive").write_text("#!/bin/sh\nexit 0\n")    # forward lost (GitHub down)
        sh("git", "push", "-q", "origin", "claude/z-1115", cwd=c)
        self.assertEqual(self.gh_ref("refs/heads/claude/z-1115"), "")
        (self.seed / "a.txt").write_text("5\n")
        sh(*G, "commit", "-qam", "main3", cwd=self.seed); sh(*G, "push", "-q", "origin", "main", cwd=self.seed)
        p = self.run_(MIRROR, "sync")
        self.assertIn("re-forward claude/z-1115", p.stdout)
        self.assertEqual(self.gh_ref("refs/heads/claude/z-1115"), sh("git", "rev-parse", "HEAD", cwd=c).stdout.strip())
        self.assertEqual(sh("git", "rev-parse", "main", cwd=self.m).stdout.strip(), self.gh_ref("refs/heads/main"))

    def test_fix_repoints_an_owner_checkout_clone_and_audit_lists_it(self):
        owner = self.d / "OpenTallas"
        sh(*G, "clone", "-q", str(self.gh), str(owner))
        root = self.d / "lanes"; root.mkdir()
        old = root / "old"
        sh(*G, "clone", "-q", str(owner), str(old))
        p = self.run_(CLONE, "--audit", str(root), ok=False)
        self.assertNotEqual(p.returncode, 0); self.assertIn(str(old), p.stdout)
        self.run_(CLONE, "--fix", str(old))
        self.assertEqual(sh("git", "remote", "get-url", "origin", cwd=old).stdout.strip(), str(self.m))
        self.assertEqual(sh("git", "config", "remote.old-origin.pushurl", cwd=old).stdout.strip(), "DISABLED")
        self.assertIn("0 clone(s)", self.run_(CLONE, "--audit", str(root)).stdout)


if __name__ == "__main__":
    unittest.main()
