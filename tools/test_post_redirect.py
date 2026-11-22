import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("pr", Path(__file__).with_name("post_redirect.py"))
pr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pr)

ST = {
    "A": ("stood-down", "B", "x"),
    "B": ("stood-down", "C", "x"),
    "C": ("live", "", "x"),
    "L1": ("stood-down", "L2", "x"),
    "L2": ("stood-down", "L1", "x"),
}


class RedirectTests(unittest.TestCase):
    def test_chain(self):
        self.assertEqual(pr.resolve("A", ST), ["B", "C"])
        self.assertEqual(pr.resolve("C", ST), [])
        self.assertEqual(pr.resolve("ZZ", ST), [])

    def test_cycle(self):
        self.assertEqual(pr.resolve("L1", ST), ["L2"])

    def test_rewrite_adds_final_successor(self):
        t, n = pr.rewrite("- 2026 X [Q -> A, COORD; cc D] hi\n  more", ST)
        self.assertIn("[Q -> A, COORD, C; cc D]", t)
        self.assertTrue(t.endswith("\n  more"))
        self.assertEqual(len(n), 1)
        self.assertIn("REDIRECTED A -> C", n[0])

    def test_no_dup_and_live_untouched(self):
        t, n = pr.rewrite("- 2026 X [Q -> A, C] hi", ST)
        self.assertEqual(t, "- 2026 X [Q -> A, C] hi")
        t, n = pr.rewrite("- 2026 X [Q -> C] hi", ST)
        self.assertEqual((t, n), ("- 2026 X [Q -> C] hi", []))

    def test_no_header(self):
        self.assertEqual(pr.rewrite("plain", ST), ("plain", []))

    def test_post_sh_end_to_end(self):
        coord_post = Path(__file__).resolve().parents[1] / "bin" / "post.sh"
        if not coord_post.exists():
            self.skipTest("no post.sh")
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "lanes").mkdir()
            (Path(d) / "lanes/LANE-STATUS.tsv").write_text("lane\tstatus\tsuccessor\tupdated\nA\tstood-down\tC\t2026-11-20\n")
            (Path(d) / "bin").mkdir()
            (Path(d) / "bin/coord-commit.sh").write_text("#!/bin/bash\nexit 0\n")
            (Path(d) / "tools").mkdir()
            (Path(d) / "tools/post_redirect.py").write_text(Path(pr.__file__).read_text())
            import os
            r = subprocess.run(["bash", str(coord_post), "T", "TAG [T -> A] x"], capture_output=True, text=True,
                               env={**os.environ, "COORD_DIR": d})
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("REDIRECTED A -> C", r.stderr)
            self.assertIn("[T -> A, C]", (Path(d) / "lanes/posts/T.md").read_text())


class ResolveLaneTests(unittest.TestCase):
    """FLOW-FIX-0100 (FABLE-FLOW-2350 b): one case-folded resolver"""
    def test_status_case_folded_and_chain(self):
        self.assertEqual(pr.resolve_lane("a", ST), "A")
        self.assertEqual(pr.resolve("a", ST), ["B", "C"])

    def test_existing_posts_file_prefers_non_lowercase_twin(self):
        with tempfile.TemporaryDirectory() as d:
            for n in ("FLOW-X-R2.md", "flow-x-r2.md", "mq1.md"):
                Path(d, n).write_text("")
            self.assertEqual(pr.resolve_lane("flow-x-r2", {}, d), "FLOW-X-R2")
            self.assertEqual(pr.resolve_lane("MQ1", {}, d), "mq1")
            self.assertEqual(pr.resolve_lane("brand-new", {}, d), "brand-new")


if __name__ == "__main__":
    unittest.main()


def test_unregistered_higher_r_successor_ends_the_chain():
    import post_redirect as PR
    st = {"A": ("stood-down", "A-R2", ""), "A-R2": ("stood-down", "A-R3", ""), "A-R3": ("stood-down", "A-R4", "")}
    PR.KNOWN.clear(); PR.KNOWN.update({"A-R4", "A-R5", "B-R9"})
    try:
        assert PR.resolve("A", st) == ["A-R2", "A-R3", "A-R4", "A-R5"]
        assert PR.live_lane("A-R3", st)[0] == "A-R5"
        assert PR.resolve("A-R5", st) == []            # the live lane itself: nothing above it
        assert PR.resolve("B", {}) == []              # a live lane without a stand-down row is never moved by a sibling
    finally:
        PR.KNOWN.clear()


def test_reclaim_by_earlier_lane():
    # COORD 11-22: R6 stood down back to R5 -> R5 is live again, posts to R5 stay on R5
    st = {"X-R4": ("stood-down", "X-R5"), "X-R6": ("stood-down", "X-R5")}
    assert pr.resolve("X-R5", st) == []
    assert pr.resolve("X-R4", st) == ["X-R5"]
    assert pr.resolve("X-R6", st) == ["X-R5"]
