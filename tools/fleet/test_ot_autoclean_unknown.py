"""FLEET-2 11-12 RUN-DIR LOSS: class a never deletes an attempt the kit-wave state does not know (negative control), still
deletes a terminal one (positive control), and keeps layout_review/ geom/ gen/ of an attempt awaiting its visual verdict.
    python3 -I tools/fleet/test_ot_autoclean_unknown.py"""
import os
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_ot_autoclean_auto as T   # noqa: E402


class Unknown(T.Base):
    def attempt(self, rel, item, n, vis=None, vis_old=True):
        d = os.path.join(self.root, rel, f"items/{item}/attempt_{n}")
        T.touch(os.path.join(d, f"gen/{item}/run/results/asap7/dp_{item}/base/3_place.odb"))
        if vis:
            T.touch(os.path.join(d, vis, "view.png"), 10, T.OLD if vis_old else time.time() - 600)
        T.age_tree(d)
        if vis and not vis_old:
            os.utime(os.path.join(d, vis), (time.time() - 600,) * 2)
            os.utime(os.path.join(d, vis, "view.png"), (time.time() - 600,) * 2)
        return d

    def terminal(self, *dirs):
        self.kw = {"attempts": {"hx:" + d: {"active": False, "signed": False, "terminal": ["FAIL/None"]} for d in dirs},
                   "latest": {}, "keep": []}

    def run_a(self, aggressive=True):
        return self.run_job("--classes", "a", *(["--aggressive"] if aggressive else []))

    def test_unknown_row_never_deleted_aggressive(self):          # negative control (the 11-12 incident)
        d = self.attempt("kw-x/kit-wave/qkv/ev1", "kv3_hgi", 1)
        self.kw = {"attempts": {}, "latest": {}, "keep": []}
        for aggr in (True, False):
            self.run_a(aggr)
            self.assertTrue(os.path.isdir(d), f"unknown row deleted (aggressive={aggr})")

    def test_lane_run_root_without_state_row_kept(self):
        d = self.attempt("vislayout2-qc/sta/runs/a", "sle_st_a_v2", 1)
        other = self.attempt("kw-x/kit-wave/qkv/ev1", "kv3_x", 1)
        self.terminal(other)
        self.run_a()
        self.assertTrue(os.path.isdir(d))
        self.assertFalse(os.path.exists(other))                   # positive control: the terminal row still goes

    def test_terminal_row_deleted(self):
        d = self.attempt("kw-x/kit-wave/qkv/ev1", "kv3_hgi", 1)
        self.terminal(d)
        self.run_a()
        self.assertFalse(os.path.exists(d))

    def test_young_layout_review_or_geom_kept_without_list(self):
        for vis in ("layout_review", "geom"):
            with self.subTest(vis=vis):
                d = self.attempt("kw-x/kit-wave/qkv/ev1", "kv3_" + vis, 1, vis=vis, vis_old=False)
                self.terminal(d)
                self.run_a()
                self.assertTrue(os.path.isdir(os.path.join(d, vis)))
                self.assertTrue(os.path.isdir(os.path.join(d, "gen")))

    def test_visual_hold_list_keeps_old_attempt(self):
        d = self.attempt("kw-x/kit-wave/qkv/ev1", "kv3_wv", 1, vis="layout_review", vis_old=True)
        self.terminal(d)
        os.makedirs(self.snap, exist_ok=True)
        with open(os.path.join(self.snap, "visual_hold.txt"), "w") as f:
            f.write("kv3_wv\n")
        self.run_a()
        self.assertTrue(os.path.isdir(os.path.join(d, "layout_review")))
        self.assertTrue(os.path.isdir(os.path.join(d, "gen")))

    def test_old_judged_attempt_with_list_present_deleted(self):
        d = self.attempt("kw-x/kit-wave/qkv/ev1", "kv3_ok", 1, vis="geom", vis_old=True)
        self.terminal(d)
        os.makedirs(self.snap, exist_ok=True)
        with open(os.path.join(self.snap, "visual_hold.txt"), "w") as f:
            f.write("some_other_item\n")
        self.run_a()
        self.assertFalse(os.path.exists(d))


if __name__ == "__main__":
    unittest.main()
