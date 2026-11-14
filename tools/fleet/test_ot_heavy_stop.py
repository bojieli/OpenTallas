"""ot-heavy-stop: container-to-scope matching by the pid in the container name"""
import importlib.machinery, importlib.util, pathlib, subprocess, unittest

P = str(pathlib.Path(__file__).with_name("ot-heavy-stop"))
loader = importlib.machinery.SourceFileLoader("ot_heavy_stop", P)
M = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_heavy_stop", loader))
loader.exec_module(M)


class Stop(unittest.TestCase):
    def test_owner_pid_of_the_name_patterns(self):
        self.assertEqual(M.owner_pid("dpkit-col_h9_r0_p5__t1__pvee6f8140-3328657"), 3328657)
        self.assertEqual(M.owner_pid("dpkit-serdes__t4-2999799-lec"), 2999799)
        self.assertEqual(M.owner_pid("otc-121627-4501"), 121627)
        self.assertEqual(M.owner_pid("kqc-qfd_dv_s5_ctl-3917879"), 3917879)
        self.assertIsNone(M.owner_pid("magical_fermi"))

    def test_select_containers_by_scope_pids(self):
        names = ["dpkit-a-100", "dpkit-a-100-lec", "dpkit-b-200", "otc-100-77", "magical_fermi"]
        self.assertEqual(M.select_containers(names, [100, 5]), ["dpkit-a-100", "dpkit-a-100-lec", "otc-100-77"])
        self.assertEqual(M.select_containers(names, []), [])

    def test_requires_a_selector(self):
        with self.assertRaises(SystemExit):
            M.main([])

    def test_dry_run_on_a_live_scope_lists_and_stops_nothing(self):
        r = subprocess.run([P, "--dry-run", "--match", "no-such-job-xyz-123"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn("0 scope(s) matched", r.stdout)


if __name__ == "__main__":
    unittest.main()
