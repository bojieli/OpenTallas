"""NEEDS_RTL bench reasons name why an rc=0 bench did not pass (regex miss / vacuous / ok check)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import closure_loop as CL  # noqa: E402


class BenchWhy(unittest.TestCase):
    def test_causes(self):
        st = {"key": "bench_equiv_m0", "expect": "pass", "pass_regex": "^EQUIV MUT=0 .* PASS$"}
        self.assertIn("pass_regex", CL.bench_why({}, st, 0))
        j = {"bench_work": {"bench_exact": "vacuous: min_count_regex 'checks=(\\\\d+)' counts []"}}
        self.assertIn("vacuous", CL.bench_why(j, {"key": "bench_exact", "expect": "pass"}, 0))
        self.assertEqual(CL.bench_why({}, {"key": "b", "expect": "pass"}, 0, False), " (ok check failed)")
        self.assertEqual(CL.bench_why({}, st, 1), "")
        self.assertEqual(CL.bench_why({}, dict(st, expect="fail"), 0), "")

    def test_reason_match_keeps_old_and_suffixed(self):
        r = {"expect": "pass", "rc": 0}
        self.assertTrue(CL._bench_reason_is("bench_x expected PASS but rc=0", "bench_x", r))
        self.assertTrue(CL._bench_reason_is("bench_x expected PASS but rc=0 (pass_regex 'a' not matched)", "bench_x", r))
        self.assertFalse(CL._bench_reason_is("bench_x expected PASS but rc=01", "bench_x", r))
        self.assertFalse(CL._bench_reason_is("bench_y expected PASS but rc=0", "bench_x", r))


if __name__ == "__main__":
    unittest.main()
