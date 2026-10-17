"""bench_count: min_count_regex must compile with exactly one capture group (ROOT 2026-10-16)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bench_count as BC


class T(unittest.TestCase):
    def test_shapes(self):
        ok = [{"name": "a", "min_count_regex": r"checks=(\d+)"}, {"name": "b", "min_count_regex": r"(?:x|y) n=(\d+)"},
              {"name": "c"}]
        self.assertEqual(BC.count_regex_errors(ok), [])
        e = BC.count_regex_errors([{"name": "z", "min_count_regex": r"checks=\d+"}])
        self.assertEqual(e, ["bench z: min_count_regex needs one capture group around the count: 'checks=\\\\d+'"])
        self.assertIn("has 2 groups", BC.count_regex_errors([{"name": "t", "min_count_regex": r"(a|b) (\d+)"}])[0])
        self.assertIn("does not compile", BC.count_regex_errors([{"name": "u", "min_count_regex": r"(\d+"}])[0])

    def test_bench_lint_git(self):
        files = {"physical/x/bench.sh": "#!/bin/bash\n# git show is fine in a comment\ngit show abc:rtl/a.sv > a.sv\n",
                 "physical/x/ok.sh": "git rev-parse HEAD 2>/dev/null || echo nogit\n",
                 "physical/x/if.sh": 'if [ -f a ];then cp a b;else git show "x:a" > b;fi\nif git rev-parse -q x; then git show x:a; fi\n',
                 "tools/b.py": "subprocess.run(['git', '-C', root, 'show', ref])\n"}
        show = files.get
        e, _ = BC.bench_lint([{"name": "a", "expect": "pass", "cmd": "bash {SRC}/physical/x/bench.sh"}], show)
        self.assertEqual(len(e), 1); self.assertIn("NON-GIT", e[0]); self.assertIn("physical/x/bench.sh:3", e[0])
        e, _ = BC.bench_lint([{"name": "a", "expect": "pass", "cmd": "bash physical/x/ok.sh"}], show)
        self.assertEqual(e, [])
        self.assertEqual(BC.bench_lint([{"name": "a", "expect": "pass", "cmd": "bash physical/x/if.sh"}], show)[0], [])
        e, _ = BC.bench_lint([{"name": "a", "expect": "pass", "cmd": "python3 tools/b.py"}], show)
        self.assertEqual(len(e), 1)
        e, _ = BC.bench_lint([{"name": "a", "expect": "pass", "cmd": "git -C {SRC} log -1; make"}])
        self.assertEqual(len(e), 1)
        e, _ = BC.bench_lint([{"name": "a", "expect": "pass", "cmd": "bash physical/x/bench.sh",
                               "git_fallback": "bench.sh copies a.sv from extra_paths when git is absent"}], show)
        self.assertEqual(e, [])
        e, _ = BC.bench_lint([{"name": "a", "expect": "pass", "cmd": "bash {RUN}/digit.sh; echo legit"}], show)
        self.assertEqual(e, [])

    def test_bench_lint_regex(self):
        files = {"w/mut.log": "ERROR: mismatch at word 7\nFAIL mismatches=3\n"}
        e, w = BC.bench_lint([{"name": "m", "expect": "fail", "cmd": "x"}], files.get)
        self.assertEqual(e, []); self.assertIn("without fail_regex", w[0])
        e, w = BC.bench_lint([{"name": "m", "expect": "fail", "cmd": "x", "fail_regex": "^FAIL mism"}], files.get)
        self.assertEqual(e, []); self.assertIn("not verified", w[0])
        e, w = BC.bench_lint([{"name": "m", "expect": "fail", "cmd": "x", "fail_regex": "^FAIL mism",
                               "fail_witness": "w/mut.log"}], files.get)
        self.assertEqual((e, w), ([], []))
        e, _ = BC.bench_lint([{"name": "m", "expect": "fail", "cmd": "x", "fail_regex": "^MUTANT DETECTED",
                               "fail_witness": "w/mut.log"}], files.get)
        self.assertIn("does not match", e[0])
        e, _ = BC.bench_lint([{"name": "m", "expect": "fail", "cmd": "x", "fail_regex": "^X",
                               "fail_witness": "w/none.log"}], files.get)
        self.assertIn("not in the source commit", e[0])
        e, _ = BC.bench_lint([{"name": "m", "expect": "pass", "cmd": "x", "pass_regex": "(PASS"}])
        self.assertIn("does not compile", e[0])


if __name__ == "__main__":
    unittest.main()
