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


if __name__ == "__main__":
    unittest.main()
