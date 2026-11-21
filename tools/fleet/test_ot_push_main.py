"""ot-push-main: rebase + touched-file tests + push; non-fast-forward retry; conflict leaves the clone unchanged; red tests push nothing."""
import importlib.machinery, importlib.util, os, pathlib, subprocess as S, sys, tempfile, unittest

P = str(pathlib.Path(__file__).with_name("ot-push-main"))
ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")


def load():
    ld = importlib.machinery.SourceFileLoader("ot_push_main_mod", P)
    m = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_push_main_mod", ld)); ld.exec_module(m)
    return m


def sh(*a, cwd=None):
    return S.run(a, cwd=cwd, env=ENV, capture_output=True, text=True, check=True).stdout.strip()


class PushMain(unittest.TestCase):
    def setUp(self):
        self.d = d = pathlib.Path(tempfile.mkdtemp())
        sh("git", "init", "-q", "--bare", "-b", "main", str(d / "o.git"))
        for n in ("a", "b"):
            sh("git", "clone", "-q", str(d / "o.git"), str(d / n))
        a = d / "a"
        (a / "tools/x").mkdir(parents=True)
        (a / "tools/x/mod.py").write_text("def f():\n    return 1\n")
        (a / "tools/x/other.py").write_text("X = 1\n")
        (a / "tools/x/test_mod.py").write_text("import os, sys\nsys.path.insert(0, os.path.dirname(__file__))\nimport mod\n\ndef test_f():\n    assert mod.f() >= 1\n")
        sh("git", "add", "-A", cwd=a); sh("git", "commit", "-qm", "base", cwd=a); sh("git", "push", "-q", "origin", "HEAD:main", cwd=a)
        sh("git", "pull", "-q", "origin", "main", cwd=d / "b")

    def run_(self, who, *args):
        return S.run([sys.executable, "-I", P, *args], cwd=self.d / who, env=ENV, capture_output=True, text=True, timeout=600)

    def commit(self, who, rel, text):
        (self.d / who / rel).write_text(text)
        sh("git", "commit", "-qam", rel, cwd=self.d / who)

    def main(self):
        return sh("git", "-C", str(self.d / "o.git"), "rev-parse", "main")

    def test_green_pushes_and_second_run_is_a_noop(self):
        self.commit("a", "tools/x/mod.py", "def f():\n    return 2\n")
        r = self.run_("a"); self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("PUSHED", r.stdout); self.assertEqual(self.main(), sh("git", "rev-parse", "HEAD", cwd=self.d / "a"))
        r = self.run_("a"); self.assertEqual(r.returncode, 0); self.assertIn("nothing to push", r.stdout)

    def test_red_tests_push_nothing(self):
        m = self.main()
        self.commit("a", "tools/x/mod.py", "def f():\n    return 0\n")
        r = self.run_("a")
        if "no pytest" in r.stdout:
            self.skipTest("no pytest")
        self.assertEqual(r.returncode, 4, r.stdout + r.stderr); self.assertEqual(self.main(), m)

    def test_behind_main_is_rebased_not_merged(self):
        self.commit("b", "tools/x/other.py", "X = 2\n")
        self.assertEqual(self.run_("b").returncode, 0)
        self.commit("a", "tools/x/mod.py", "def f():\n    return 3\n")       # a is behind
        r = self.run_("a"); self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        log = sh("git", "-C", str(self.d / "o.git"), "log", "--format=%s", "-3", "main").split("\n")
        self.assertEqual(log, ["tools/x/mod.py", "tools/x/other.py", "base"])   # linear, no merge commit

    def test_conflict_leaves_clone_unchanged_and_exits_3(self):
        self.commit("b", "tools/x/mod.py", "def f():\n    return 5\n")
        self.assertEqual(self.run_("b").returncode, 0)
        self.commit("a", "tools/x/mod.py", "def f():\n    return 4\n")
        head = sh("git", "rev-parse", "HEAD", cwd=self.d / "a")
        r = self.run_("a"); self.assertEqual(r.returncode, 3, r.stdout + r.stderr); self.assertIn("tools/x/mod.py", r.stdout)
        self.assertEqual(sh("git", "rev-parse", "HEAD", cwd=self.d / "a"), head)
        self.assertEqual(sh("git", "status", "--porcelain", "--untracked-files=no", cwd=self.d / "a"), "")

    def test_non_fast_forward_race_is_retried(self):
        hook = self.d / "o.git/hooks/pre-receive"
        flag = self.d / "raced"
        hook.write_text(f'#!/bin/bash\nif [ ! -e {flag} ]; then touch {flag}; echo "ot-git-mirror: main NOT pushed: moved" >&2; exit 1; fi\n')
        hook.chmod(0o755)
        self.commit("a", "tools/x/other.py", "X = 9\n")
        r = self.run_("a"); self.assertEqual(r.returncode, 0, r.stdout + r.stderr); self.assertIn("attempt 2", r.stdout)

    def test_dirty_tree_is_refused(self):
        (self.d / "a/tools/x/other.py").write_text("X = 77\n")
        self.assertEqual(self.run_("a").returncode, 2)

    # PUSH-FIX-2300 -------------------------------------------------------------------------------------------------------------
    def sparse_clone(self, reader_src):
        """b (full clone) publishes tools/y + physical/cfg/data.json; a becomes a sparse clone with only tools/"""
        b = self.d / "b"
        (b / "tools/y").mkdir(parents=True); (b / "physical/cfg").mkdir(parents=True)
        (b / "physical/cfg/data.json").write_text("[1]\n")
        (b / "tools/y/mod.py").write_text("V = 1\n")
        (b / "tools/y/test_mod.py").write_text(reader_src)
        sh("git", "add", "-A", cwd=b); sh("git", "commit", "-qm", "y", cwd=b); sh("git", "push", "-q", "origin", "HEAD:main", cwd=b)
        a = self.d / "a"
        sh("git", "pull", "-q", "origin", "main", cwd=a)
        sh("git", "sparse-checkout", "init", "--cone", cwd=a); sh("git", "sparse-checkout", "set", "tools", cwd=a)
        self.assertFalse((a / "physical").exists())
        self.commit("a", "tools/y/mod.py", "V = 2\n")
        return a

    def test_sparse_cone_widened_for_named_paths(self):
        a = self.sparse_clone("import os\n\ndef test_r():\n    assert os.path.exists('physical/cfg/data.json')\n")
        r = self.run_("a")
        if "no pytest" in r.stdout:
            self.skipTest("no pytest")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr); self.assertIn("widened sparse cone (+physical/cfg)", r.stdout)
        self.assertTrue((a / "physical/cfg/data.json").exists()); self.assertIn("PUSHED", r.stdout)

    def test_sparse_cone_widened_after_failure_names_missing_path(self):
        a = self.sparse_clone("import pathlib\nR = pathlib.Path(__file__).resolve().parents[2]\n\ndef test_r():\n"
                              "    assert (R / 'physical' / 'cfg' / 'data.json').read_text() == '[1]\\n'\n")
        r = self.run_("a")
        if "no pytest" in r.stdout:
            self.skipTest("no pytest")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr); self.assertIn("cone widened after failure", r.stdout)
        self.assertTrue((a / "physical/cfg/data.json").exists())

    def test_genuine_red_still_blocks_after_widening(self):
        self.sparse_clone("def test_r():\n    assert False\n")
        m = self.main()
        r = self.run_("a")
        if "no pytest" in r.stdout:
            self.skipTest("no pytest")
        self.assertEqual(r.returncode, 4, r.stdout + r.stderr); self.assertEqual(self.main(), m)

    def test_affected_tests_only_rerun_on_overlap(self):
        m = load()
        tests = ["tools/x/test_mod.py", "tools/x/test_other.py"]
        files = ["tools/x/mod.py", "tools/x/other.py"]
        self.assertEqual(m.affected_tests(tests, files, ["docs/readme.md"]), [])
        self.assertEqual(m.affected_tests(tests, files, ["tools/x/other.py", "docs/a"]), [])   # no test_other.py exists on disk here
        self.assertEqual(m.affected_tests(tests, files, ["tools/x/test_other.py"]), ["tools/x/test_other.py"])
        self.assertEqual(m.affected_tests(tests, files, ["tools/x/test_mod.py", "tools/x/test_other.py"]), tests)

    def test_default_timeout_scales_with_load(self):
        m = load()
        self.assertEqual(m.default_timeout(load=1, ncpu=64), 3000)
        self.assertEqual(m.default_timeout(load=128, ncpu=64), 6000)
        self.assertEqual(m.default_timeout(load=1000, ncpu=64), 9000)
        self.assertEqual(m.default_timeout(load=0.1, ncpu=0), 3000)


if __name__ == "__main__":
    unittest.main()
