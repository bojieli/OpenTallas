"""S81-DEC3 2026-10-18: a child's "clock_tap_ps" lowers its spine target (taps it later); absent = unchanged."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ref_tile as RT  # noqa: E402


class ClockTap(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        for n, m in dict(a=275.1, b=167.7).items():
            v = self.root / "v" / n
            v.mkdir(parents=True)
            (v / "insertion.json").write_text(json.dumps({"tt": {"boundary": {"n": 9, "mean": m}}}))
        self.old, RT.ROOT = RT.ROOT, self.root

    def tearDown(self):
        RT.ROOT = self.old
        self.td.cleanup()

    def test_tap(self):
        s = dict(child_clock_ref="boundary", children=[dict(view="v/a"), dict(view="v/b", clock_tap_ps=32)])
        self.assertEqual(RT.child_insertions(s), {"a": 275.1, "b": 135.7})

    def test_no_tap_unchanged(self):
        s = dict(child_clock_ref="boundary", children=[dict(view="v/a"), dict(view="v/b")])
        self.assertEqual(RT.child_insertions(s), {"a": 275.1, "b": 167.7})


if __name__ == "__main__":
    unittest.main()
