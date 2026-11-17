import json, os, tempfile, unittest
import build_protected_live as B

R = "/srv/opentallas-scratch2/claude/"


def mk(cfg, markers=(), prose=""):
    d = tempfile.mkdtemp(); os.makedirs(d + "/autopilot"); os.makedirs(d + "/lanes/handoff")
    json.dump(cfg, open(d + "/autopilot/kit_wave.json", "w"))
    for i, m in enumerate(markers):
        json.dump(m, open(d + "/lanes/handoff/tree_switch_%d.json" % i, "w"))
    open(d + "/lanes/COORD-REVIEW-QUEUE.md", "w").write(prose)
    open(d + "/lanes/handoff/x.md", "w").write(prose)
    return d


class Live(unittest.TestCase):
    def test_current_keys_kept_history_and_prose_dropped(self):
        cfg = {"dies": {"s81": {"src": R + "kw45/src_cur", "plan": R + "kw45/src_cur/plan.json", "src_prev_d4": R + "kw45/src_old",
                                "superseded_trees": [R + "kw45/src_gone"], "rollback_tree": R + "kw45/src_rb", "note_x": "see " + R + "lane/z/deep/a",
                                "item_inputs": {"a": R + "kw45/inputs_cur/x"}, "item_inputs_prev_kw43": {"a": R + "kw43/old/in/x"}}}}
        d = mk(cfg, prose="quoted " + R + "foo/bar/baz/qux and " + R + "kw45/src_gone")
        got = B.build(d, [d + "/lanes/handoff"])
        self.assertEqual(got, {R + "kw45/src_cur", R + "kw45/src_cur/plan.json", R + "kw45/src_rb", R + "kw45/inputs_cur/x"})

    def test_markers_use_the_same_rule_and_protected_dbs_count(self):
        d = mk({"dies": {}}, markers=[{"tree": R + "kw45/src_new", "superseded_trees": [R + "kw45/src_old"], "prev_tree": R + "kw45/src_older"}])
        open(d + "/PROTECTED-DBS.txt", "w").write(R + "db/keep/me/here # why\n/tmp/nope\n")
        self.assertEqual(B.build(d, [d + "/lanes/handoff"]), {R + "kw45/src_new", R + "db/keep/me/here"})

    def test_unreadable_kit_wave_refuses_an_empty_list(self):
        with self.assertRaises(SystemExit):
            B.build(tempfile.mkdtemp(), [])
