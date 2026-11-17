"""(3) kit generation never opens a source-tree file for write: the generator tests run against a read-only copy of tools/die_plan (a-w files and dirs, bytecode off)."""
import os, shutil, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DIE_PLAN = os.path.join(HERE, "..", "die_plan")


class GenNeverWritesTheSourceTree(unittest.TestCase):
    def test_genbug_guards_pass_on_a_read_only_tree(self):
        if not os.path.isfile(os.path.join(DIE_PLAN, "gen_phys.py")):
            self.skipTest("tools/die_plan not in this checkout")
        t = tempfile.mkdtemp(); bt = tempfile.mkdtemp()        # basetemp lives outside the read-only tree
        try:
            root = os.path.abspath(os.path.join(HERE, "..", ".."))
            cf = os.path.join(root, "physical", "common_flow")
            if not os.path.isdir(cf):
                self.skipTest("physical/common_flow not in this checkout")
            shutil.copytree(cf, os.path.join(t, "physical", "common_flow"), symlinks=True)
            dst = os.path.join(t, "tools"); shutil.copytree(os.path.join(HERE, ".."), dst, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc"), symlinks=True)
            for dp, dn, fn in os.walk(t):
                for f in fn:
                    p = os.path.join(dp, f)
                    if not os.path.islink(p): os.chmod(p, os.lstat(p).st_mode & ~0o222)
            for dp, dn, fn in os.walk(t, topdown=False):
                os.chmod(dp, os.lstat(dp).st_mode & ~0o222)
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
            r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--basetemp", bt, os.path.join(dst, "die_plan", "test_genbug_guards.py")],
                               capture_output=True, text=True, env=env, timeout=600, cwd=t)
            self.assertEqual(r.returncode, 0, r.stdout[-1500:] + r.stderr[-500:])
            wrote = [os.path.join(dp, f) for dp, dn, fn in os.walk(t) for f in fn if os.lstat(os.path.join(dp, f)).st_mode & 0o222]
            self.assertEqual(wrote, [])
        finally:
            for dp, dn, fn in os.walk(t): os.chmod(dp, 0o755)
            shutil.rmtree(t, ignore_errors=True); shutil.rmtree(bt, ignore_errors=True)
