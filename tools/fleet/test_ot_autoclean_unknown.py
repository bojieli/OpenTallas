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

ac_mod = T.ac


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


class VisualHoldWriter(T.Base):
    """the driver writes <snapshot>/visual_hold.txt from lanes/VISUAL-QUEUE.tsv and kit-wave state WAIT-VISUAL rows, read from
    origin/coord/state or the hub (fresh < 15 min), never from a stale local clone"""
    VQ = ("die\ttype\tfamily\tattempt\tstate\trender_dir\tauto_geom\thost\n"
          "qc\tt1\tf\t2\tWAIT-VISUAL\t:epyc4:/r/kw/runs/qc/items/t1/attempt_2/gen/t1/run/layout_review\t"
          "epyc4:/r/kw/runs/qc/items/t1/attempt_2/geom/auto_geom.png\t\n"
          "qc\tt2\tf\t1\tWAIT-VISUAL\t:epyc4:/r/kw/runs/qc/items/t2/gen/t2/run/layout_review\t\t\n"
          "qc\tt3\tf\t1\tGOOD\t:epyc4:/r/kw/runs/qc/items/t3/attempt_1/gen/x\t\t\n")
    ST = ('{"items": {"a": {"route_hold": "WAIT-VISUAL: place done", "kit": "epyc2:/r/kw/runs/hbm/items/q1/attempt_12/gen/q1"},'
          ' "b": {"route_hold": "", "reason": "x", "kit": "epyc2:/r/kw/runs/hbm/items/q9/attempt_3/gen/q9"}}}')

    def test_paths_from_both_sources(self):
        p = ac_mod.visual_hold_paths("/x", sources=(self.VQ, self.ST))
        self.assertEqual(p, ["/r/kw/runs/hbm/items/q1/attempt_12", "/r/kw/runs/qc/items/t1/attempt_2",
                             "/r/kw/runs/qc/items/t2"])          # GOOD row and non-WAIT-VISUAL state row are not held

    def test_bad_source_writes_nothing(self):
        self.assertIsNone(ac_mod.visual_hold_paths("/x", sources=("", "not json")))
        self.assertIsNone(ac_mod.visual_hold_paths("/x", sources=(self.VQ, "not json")))

    def test_freshness_gate(self):
        now = 1000000.0
        fresh = lambda c, n: (self.VQ, self.ST, 60.0)
        stale = lambda c, n: (self.VQ, self.ST, 16 * 60.0)
        boom = lambda c, n: (_ for _ in ()).throw(OSError("git down"))
        self.assertEqual(ac_mod.fetch_hold_sources("/x", now, readers=(fresh,)), (self.VQ, self.ST))
        self.assertIsNone(ac_mod.fetch_hold_sources("/x", now, readers=(stale,)))                 # stale: no file
        self.assertIsNone(ac_mod.fetch_hold_sources("/x", now, readers=(boom, stale)))
        self.assertEqual(ac_mod.fetch_hold_sources("/x", now, readers=(boom, fresh)), (self.VQ, self.ST))   # falls through to the hub
        self.assertEqual(ac_mod.fetch_hold_sources("/x", now, readers=(stale, fresh)), (self.VQ, self.ST))  # stale first, fresh second

    def test_git_reader_reads_origin_not_working_tree(self):
        import subprocess as sp
        o = os.path.join(self.t, "origin.git")
        w = os.path.join(self.t, "w")
        sp.run(["git", "init", "-q", "--bare", "-b", "coord/state", o], check=True)
        sp.run(["git", "clone", "-q", o, w], check=True, capture_output=True)
        os.makedirs(os.path.join(w, "lanes")); os.makedirs(os.path.join(w, "autopilot"))
        with open(os.path.join(w, "lanes/VISUAL-QUEUE.tsv"), "w") as f:
            f.write(self.VQ)
        with open(os.path.join(w, "autopilot/kit_wave_state.json"), "w") as f:
            f.write(self.ST)
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        sp.run(["git", "-C", w, "add", "-A"], check=True)
        sp.run(["git", "-C", w, "commit", "-q", "-m", "x"], check=True, env=env)
        sp.run(["git", "-C", w, "push", "-q", "origin", "HEAD:coord/state"], check=True, capture_output=True)
        # a stale local clone: its working tree has an OLD list, origin has the new one
        c = os.path.join(self.t, "stale")
        sp.run(["git", "clone", "-q", "-b", "coord/state", o, c], check=True, capture_output=True)
        with open(os.path.join(c, "lanes/VISUAL-QUEUE.tsv"), "w") as f:
            f.write("die\tstate\n")
        vq, st, age = ac_mod._git_hold_sources(c, time.time())
        self.assertEqual(vq, self.VQ)
        self.assertLess(age, 300)
        self.assertEqual(ac_mod.visual_hold_paths(c, sources=(vq, st))[0], "/r/kw/runs/hbm/items/q1/attempt_12")

    def test_item_dir_entry_holds_its_attempts(self):
        d = os.path.join(self.root, "kw-x/kit-wave/qkv/ev1/items/t2/attempt_1")
        T.touch(os.path.join(d, "gen/t2/run/results/base/3_place.odb"))
        T.age_tree(d)
        self.kw = {"attempts": {"hx:" + d: {"active": False, "signed": False, "terminal": ["FAIL/None"]}}, "latest": {}, "keep": []}
        os.makedirs(self.snap, exist_ok=True)
        with open(os.path.join(self.snap, "visual_hold.txt"), "w") as f:
            f.write(os.path.dirname(d) + "\n")
        self.run_job("--classes", "a", "--aggressive")
        self.assertTrue(os.path.isdir(os.path.join(d, "gen")))


if __name__ == "__main__":
    unittest.main()
