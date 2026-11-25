"""SPARSE-RESTORE-1124: ot-push-main's temporary cone widening is undone on every exit (pushed or refused); the widened dirs leave disk."""
import os, pathlib, subprocess as S, sys, tempfile, unittest

P = str(pathlib.Path(__file__).with_name("ot-push-main"))
ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")


def sh(*a, cwd=None):
    return S.run(a, cwd=cwd, env=ENV, capture_output=True, text=True, check=True).stdout.strip()


class SparseRestore(unittest.TestCase):
    def setUp(self):
        self.d = d = pathlib.Path(tempfile.mkdtemp())
        sh("git", "init", "-q", "--bare", "-b", "main", str(d / "o.git"))
        sh("git", "clone", "-q", str(d / "o.git"), str(d / "seed"))
        s = d / "seed"
        (s / "tools/x").mkdir(parents=True)
        (s / "big/data").mkdir(parents=True)
        (s / "big/data/ref.txt").write_text("1\n")
        (s / "tools/x/mod.py").write_text("def f():\n    return 1\n")
        (s / "tools/x/test_mod.py").write_text(
            "import os, sys\nsys.path.insert(0, os.path.dirname(__file__))\nimport mod\n"
            "REF = os.path.join(os.path.dirname(__file__), '../../big/data/ref.txt')\n\n"
            "def test_f():\n    assert mod.f() >= int(open(REF).read())\n")
        sh("git", "add", "tools", "big", cwd=s); sh("git", "commit", "-qm", "base", cwd=s); sh("git", "push", "-q", "origin", "HEAD:main", cwd=s)
        sh("git", "clone", "-q", "--sparse", str(d / "o.git"), str(d / "a"))
        self.a = d / "a"
        sh("git", "sparse-checkout", "set", "tools", cwd=self.a)
        self.before = sh("git", "sparse-checkout", "list", cwd=self.a)
        self.assertFalse((self.a / "big").exists())

    def run_(self):
        return S.run([sys.executable, "-I", P], cwd=self.a, env=ENV, capture_output=True, text=True, timeout=600)

    def commit(self, text):
        (self.a / "tools/x/mod.py").write_text(text)
        sh("git", "commit", "-qam", "m", cwd=self.a)

    def check_restored(self, r):
        self.assertEqual(sh("git", "sparse-checkout", "list", cwd=self.a), self.before, r.stdout + r.stderr)
        self.assertFalse((self.a / "big").exists(), "widened dir left on disk:\n" + r.stdout)

    def test_green_push_restores_cone(self):
        self.commit("def f():\n    return 2\n")
        r = self.run_()
        if "no pytest" in r.stdout:
            self.skipTest("no pytest")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("widened sparse cone", r.stdout)
        self.assertIn("restored the original sparse cone", r.stdout)
        self.check_restored(r)

    def test_red_tests_restore_cone(self):
        self.commit("def f():\n    return 0\n")
        r = self.run_()
        if "no pytest" in r.stdout:
            self.skipTest("no pytest")
        self.assertEqual(r.returncode, 4, r.stdout + r.stderr)
        self.check_restored(r)

    def test_not_widened_is_noop(self):
        r = self.run_()       # nothing to push: no widening, no restore message
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("restored", r.stdout)
        self.check_restored(r)


if __name__ == "__main__":
    unittest.main()
