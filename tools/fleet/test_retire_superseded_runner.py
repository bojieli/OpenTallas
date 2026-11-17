import os, subprocess, unittest
H = os.path.dirname(os.path.abspath(__file__))


class Runner(unittest.TestCase):
    def test_wrapper_is_apply_guarded_and_syntax_ok(self):
        p = os.path.join(H, "ot-retire-superseded-run.sh")
        s = open(p).read()
        self.assertEqual(subprocess.run(["bash", "-n", p]).returncode, 0)
        for need in ("--apply", "--guard-module", "--list", "protected.txt", "retire_superseded.py", "exit 3"):
            self.assertIn(need, s)
