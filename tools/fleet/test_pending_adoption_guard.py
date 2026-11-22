import json, os, tempfile, time, unittest
import ot_delete_guard as G
import build_protected_live as B

R = "/srv/opentallas-scratch2/claude/"


def tree(mt, name="src_qc_pin_x_m5t"):
    d = tempfile.mkdtemp() + "/" + name; os.makedirs(d)
    open(d + "/.src-manifest.json", "w").write("{}"); os.utime(d + "/.src-manifest.json", (mt, mt)); return d


class Newer(unittest.TestCase):
    CUR = {"src_qc_": {"tree": "src_qc_pin_x_d4", "adopted_at": 1000.0}}

    def test_a_tree_published_after_the_adoption_is_refused_an_older_one_is_not(self):
        self.assertIn("newer than the die's current tree src_qc_pin_x_d4", G.newer_than_current(tree(5000), self.CUR))
        self.assertEqual(G.newer_than_current(tree(500, "src_qc_pin_x_d3"), self.CUR), "")
        self.assertEqual(G.newer_than_current(tree(5000, "src_qc_pin_x_d4"), self.CUR), "")        # the current tree itself
        self.assertEqual(G.newer_than_current(tree(5000, "src_kv_pin_y"), self.CUR), "")            # other dies unaffected
        self.assertEqual(G.newer_than_current(tree(5000, "src_qc_pin_x_m5.part"), self.CUR), "")    # partial copies are the replicate tool's

    def test_refuse_calls_it_before_the_protected_list(self):
        import inspect
        src = inspect.getsource(G.refuse)
        self.assertLess(src.index("newer_than_current"), src.index("load_list()"))


class Posts(unittest.TestCase):
    def test_trees_named_in_non_fleet_posts_of_the_last_24h_are_protected(self):
        q = tempfile.mktemp()
        now = time.mktime(time.strptime("2026-11-17 14:00", "%Y-%m-%d %H:%M"))
        open(q, "w").write("\n".join([
            "- 2026-11-17 13:0x PST RESULT [QC-PLAN-R3 -> COORD] M5T published src_qc_pin_eb_s4q9m5_tce8bcf97 apply pending",
            "- 2026-11-17 12:10 PST STATE [FLEET-OPS-R -> COORD] retired src_qc_pin_eb_old (fleet posts never protect)",
            "- 2026-11-15 09:00 PST RESULT [KV-R -> COORD] old src_kv_pin_ancient (older than 24 h)",
        ])) 
        out = set(); B.post_trees(q, out, os.path.normpath, now=now)
        self.assertEqual(out, {R + "kw45/src_qc_pin_eb_s4q9m5_tce8bcf97"})

    def test_post_approving_a_delete_does_not_protect_the_tree_clean_aggr_r3(self):
        q = tempfile.mktemp()
        now = time.mktime(time.strptime("2026-11-22 04:00", "%Y-%m-%d %H:%M"))
        open(q, "w").write("\n".join([
            "- 2026-11-22 03:05 PST RULING [COORD] (1) FAM-X READY src_s81_pin_keep_work APPROVED. (2) FLOW-Y ASK APPROVED: its trees "
            "kw45/src_s81_pin_a_work_r2, _r2b may be deleted via ot-delete. (3) other src_kv_pin_keep2 stays",
            "- 2026-11-22 03:10 PST RULING [COORD] src_qc_pin_old_work delete APPROVED",
        ]))
        out = set(); B.post_trees(q, out, os.path.normpath, now=now)
        self.assertEqual(out, {R + "kw45/src_s81_pin_keep_work", R + "kw45/src_kv_pin_keep2"})

    def test_current_trees_file_names_the_current_tree_and_its_adoption_time(self):
        c = tempfile.mkdtemp(); os.makedirs(c + "/autopilot"); os.makedirs(c + "/lanes/handoff")
        json.dump({"dies": {"qwen_compute": {"src": R + "kw45/src_qc_pin_x_d4"}}}, open(c + "/autopilot/kit_wave.json", "w"))
        open(c + "/lanes/handoff/tree_switch_qwen_compute.json", "w").write("{}"); os.utime(c + "/lanes/handoff/tree_switch_qwen_compute.json", (777, 777))
        self.assertEqual(B.current_trees(c), {"src_qc_": {"tree": "src_qc_pin_x_d4", "adopted_at": 777.0}})
