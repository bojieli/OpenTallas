"""ot-tmpfs-clean: idle, unused top-level tmpfs dirs go; recent, in-use and protected ones stay"""
import importlib.machinery, importlib.util, os, pathlib, subprocess, tempfile, time, unittest

P = str(pathlib.Path(__file__).with_name("ot-tmpfs-clean"))
loader = importlib.machinery.SourceFileLoader("ot_tmpfs_clean", P)
M = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_tmpfs_clean", loader))
loader.exec_module(M)


def mk(root, name, age_h, size=2048):
    d = os.path.join(root, name); os.makedirs(os.path.join(d, "sub"))
    f = os.path.join(d, "sub", "data"); open(f, "wb").write(b"x" * size)
    t = time.time() - age_h * 3600
    for p in (f, os.path.join(d, "sub"), d):
        os.utime(p, (t, t))
    return d


class Clean(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def test_idle_dir_is_a_candidate_recent_and_protected_are_not(self):
        mk(self.root, "rm57", 40); mk(self.root, "recent", 2); mk(self.root, "systemd-private-abc", 99); mk(self.root, ".X11-unix", 99)
        open(os.path.join(self.root, "loosefile"), "w").write("x")
        names = [os.path.basename(p) for p, _ in M.candidates([self.root], time.time(), 24 * 3600)]
        self.assertEqual(names, ["rm57"])

    def test_a_fresh_file_deep_inside_keeps_the_dir(self):
        d = mk(self.root, "busy", 40)
        open(os.path.join(d, "sub", "new"), "w").write("y")                       # written now
        self.assertEqual(M.candidates([self.root], time.time(), 24 * 3600), [])

    def test_in_use_by_cwd_or_open_file(self):
        d = mk(self.root, "held", 40)
        p = subprocess.Popen(["sleep", "30"], cwd=os.path.join(d, "sub"))
        try:
            self.assertTrue(M.in_use(d))
        finally:
            p.kill(); p.wait()
        self.assertFalse(M.in_use(d))
        fh = open(os.path.join(d, "sub", "data"), "rb")
        try:
            self.assertTrue(M.in_use(d))
        finally:
            fh.close()

    def test_run_removes_only_the_idle_unused_dir(self):
        a, b = mk(self.root, "old", 50), mk(self.root, "new", 1)
        M.LOG = os.path.join(self.root, "log.txt")
        M.main(["--root", self.root])
        self.assertFalse(os.path.exists(a)); self.assertTrue(os.path.exists(b))
        self.assertIn("REMOVED", open(M.LOG).read())

    def test_dry_run_removes_nothing(self):
        a = mk(self.root, "old", 50)
        M.main(["--dry-run", "--root", self.root])
        self.assertTrue(os.path.exists(a))


    def test_path_named_in_a_waiter_command_line_or_a_unit_is_kept(self):
        d = mk(self.root, "queued", 50)
        p = subprocess.Popen(["python3", "-c", "import time; time.sleep(30)", d])                                    # stands in for an ot-heavy waiter naming the dir
        time.sleep(0.2)
        try:
            self.assertTrue(M.in_use(d))
        finally:
            p.kill(); p.wait()
        units = tempfile.mkdtemp()
        open(os.path.join(units, "job.service"), "w").write(f"[Service]\nExecStart=/bin/true {d}\n")
        self.assertTrue(M.named_in_units(d, dirs=(units,)))
        self.assertFalse(M.named_in_units("/nonexistent/zzz", dirs=(units,)))


if __name__ == "__main__":
    unittest.main()
