"""S81-DIE-R3 11-19: auto-retire never retires a lane dir in use: written in the last 24 h (the lane window never drops below 24 h even when the
attempt window is 12 h), a live process with cwd / open files under it, a path named in a lane handoff of the last 24 h."""
import os, sys, tempfile, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import auto_retire as ar


class InUse(unittest.TestCase):
    def mk(self, root, rel, age_h):
        p = os.path.join(root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w").write("x")
        t = time.time() - age_h * 3600
        os.utime(p, (t, t))
        for d in (os.path.dirname(p),):
            os.utime(d, (t, t))
        return p

    def test_lane_window_is_24h_even_when_runner_says_12(self):
        self.assertEqual(ar.lane_idle_h(12), 24.0)
        self.assertEqual(ar.lane_idle_h(48), 48.0)
        with tempfile.TemporaryDirectory() as claude:
            self.mk(claude, "s81-die-r3-e8/tools/a.py", 13.6)       # idle 13.6 h: the 11-19 17:38 deletion
            self.mk(claude, "s81-die-r3-e8/old/a.py", 40)
            got = {p for p, _ in ar.lane_candidates(claude, idle_h=ar.lane_idle_h(12), mtime=ar.newest_mtime)}
            self.assertNotIn(os.path.join(claude, "s81-die-r3-e8/tools"), got)
            self.assertNotIn(os.path.join(claude, "s81-die-r3-e8"), got)

    def test_live_process_cwd_or_fd_under_the_dir_is_live(self):
        with tempfile.TemporaryDirectory() as claude, tempfile.TemporaryDirectory() as proc:
            d = os.path.join(proc, "4242"); os.makedirs(os.path.join(d, "fd"))
            tree = os.path.join(claude, "lane1", "gitshim"); os.makedirs(tree)
            os.symlink(tree + "/bin", os.path.join(d, "cwd"))
            lr = ar.LiveRefs(claude, proc=proc, ttl=0)
            self.assertTrue(lr.hit(tree))
            self.assertFalse(lr.hit(os.path.join(claude, "lane2", "x")))

    def test_path_named_in_a_handoff_text_is_refused(self):
        self.assertTrue(ar.post_text_hit("/srv/s/claude/s81-die-r3-e8/tools", "- handoff: build uses /srv/s/claude/s81-die-r3-e8/tools/bin/x\n"))
        self.assertFalse(ar.post_text_hit("/srv/s/claude/s81-die-r3-e8/tools", "- other lane /srv/s/claude/s81-die-r3-e9/tools\n"))

    def test_child_of_a_named_lane_dir_is_refused(self):
        posts = "- RESULT build in /srv/s/claude/kv-d23-compose8 (W/x)\n"
        self.assertTrue(ar.post_text_hit("/srv/s/claude/kv-d23-compose8/gatein", posts))
        self.assertTrue(ar.post_text_hit("/srv/s/claude/kv-d23-compose8", posts))
        self.assertFalse(ar.post_text_hit("/srv/s/claude/kv-d23-compose9/gatein", posts))
        self.assertFalse(ar.post_text_hit("/srv/s/claude/kv-d23-compose8x/gatein", posts))

    def test_superseded_src_tree_named_in_a_post_is_kept(self):
        p = "- STATE build5 needs kw45/src_s81_pin_3c913dbdfb23_d8h_1119_work (D8i base)\n"
        self.assertTrue(ar.name_hit("/srv/s/claude/kw45/src_s81_pin_3c913dbdfb23_d8h_1119_work", p))
        self.assertFalse(ar.name_hit("/srv/s/claude/kw45/src_s81_pin_3c913dbdfb23_d8h_1119", p + "x"))
        self.assertFalse(ar.name_hit("/srv/s/claude/kw45/src_s81_other", p))

    def test_run_refuses_a_src_tree_a_live_job_or_post_names(self):
        import tempfile, os, time, json, shutil
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d)
        root = os.path.join(d, "kw45"); now = time.time()
        for n, age in (("src_kv_a", 500), ("src_kv_b", 400), ("src_kv_c", 100)):
            os.makedirs(os.path.join(root, n)); os.utime(os.path.join(root, n), (now - age, now - age))
        old = os.path.join(root, "src_kv_a")
        cfg = {"dies": {"qwen_kvsys": {"src": os.path.join(root, "src_kv_c"), "superseded_trees": [old]}}}
        texts = [json.dumps(cfg), "", ""]
        class L:
            def __init__(self, h): self.h = h
            def hit(self, p): return self.h
        def run(posts="", live=None):
            return ar.run(root, cfg, texts, set(), lambda t: "", lambda _: None, 999, free=lambda: 1.0, posts=posts, live=live)
        self.assertEqual(run()[0]["result"], "WOULD-DELETE")                      # the tree IS a candidate
        r = run(live=L(old + "/f"))[0]["result"]
        self.assertTrue(r.startswith("REFUSED: live input") and "queued" in r)
        self.assertIn("hub post", run(posts="- build5 needs kw45/src_kv_a\n")[0]["result"])
        self.assertIn("hub post", run(posts="- x " + old + " y\n")[0]["result"])
        self.assertEqual(run(posts="- other src_kv_aX\n", live=L(""))[0]["result"], "WOULD-DELETE")
        self.assertTrue(os.path.isdir(old))

    def test_runner_adds_handoffs_to_the_posts_input(self):
        sh = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ot-auto-retire-run.sh")).read()
        self.assertGreaterEqual(sh.count("lanes/handoff"), 2)
        self.assertIn("-mtime -1", sh)


if __name__ == "__main__":
    unittest.main()
