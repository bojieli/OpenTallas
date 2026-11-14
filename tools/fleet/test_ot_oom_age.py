"""ot-oom-age: youngest build processes get the highest oom_score_adj (killed first), old ones decay to 0."""
import importlib.machinery, importlib.util, os, pathlib, shutil, subprocess, sys, tempfile, time, unittest

P = str(pathlib.Path(__file__).with_name("ot-oom-age"))
loader = importlib.machinery.SourceFileLoader("ot_oom_age", P)
M = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_oom_age", loader))
loader.exec_module(M)


class Age(unittest.TestCase):
    def test_target_decays_100_per_hour_to_zero(self):
        self.assertEqual([M.target_adj(s) for s in (0, 3599, 3600, 7200, 8 * 3600, 20 * 3600)], [800, 800, 700, 600, 0, 0])

    def test_only_adj_inside_0_800_is_managed(self):
        self.assertTrue(M.managed(0) and M.managed(800) and M.managed(300))
        self.assertFalse(M.managed(-999) or M.managed(900) or M.managed(1000))

    def test_dummy_pair_young_vs_aged(self):
        d = tempfile.mkdtemp(); exe = os.path.join(d, "openroad"); shutil.copy("/bin/sleep", exe)
        a = subprocess.Popen([exe, "60"]); b = subprocess.Popen([exe, "60"])
        try:
            time.sleep(0.2)
            # raising own children above their current adj needs no privilege; lowering does, so start both at 800 and age one
            for p in (a, b):
                open(f"/proc/{p.pid}/oom_score_adj", "w").write("800")
            M.main(["--pid", str(a.pid), "--comm", "openroad", "--now-offset", "7200"])    # a looks 2 h old -> 600 (needs CAP_SYS_RESOURCE)
            M.main(["--pid", str(b.pid), "--comm", "openroad"])                              # b is new -> stays 800
            ja, jb = int(open(f"/proc/{a.pid}/oom_score_adj").read()), int(open(f"/proc/{b.pid}/oom_score_adj").read())
            self.assertEqual(jb, 800)
            if os.geteuid() == 0:
                self.assertEqual(ja, 600)
                self.assertGreater(int(open(f"/proc/{b.pid}/oom_score").read()), int(open(f"/proc/{a.pid}/oom_score").read()))
        finally:
            a.kill(); b.kill()


if __name__ == "__main__":
    unittest.main()
