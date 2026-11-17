import json, os, tempfile, time, unittest
import auto_retire as A


def mk(trees, signed=None):
    root = tempfile.mkdtemp(); now = time.time()
    for i, (n, age) in enumerate(trees):
        os.makedirs(os.path.join(root, n)); open(os.path.join(root, n, "f"), "w").write("x")
        os.utime(os.path.join(root, n), (now - age, now - age))
    return root


class Select(unittest.TestCase):
    def test_keeps_current_rollback_newer_and_referenced(self):
        trees = ["src_kv_d1", "src_kv_d2", "src_kv_d3", "src_kv_d4", "src_kv_d5", "src_kv_d6"]
        mt = {"src_kv_d1": 10, "src_kv_d2": 20, "src_kv_d3": 30, "src_kv_d4": 40, "src_kv_d5": 50, "src_kv_d6": 60}   # d5 current, d6 pending adoption
        cfg = {"dies": {"qwen_kvsys": {"src": "/x/kw45/src_kv_d5"}}}
        texts = [json.dumps(cfg) + " /x/kw45/src_kv_d2 ", "", ""]                                # d2 is named (e.g. src_prev_*)
        out = A.select(trees, cfg, texts, mt)
        self.assertEqual(out, ["src_kv_d1", "src_kv_d3"])        # d5 current, d6 newer, d2 referenced, d4 = the one rollback
        self.assertNotIn("src_kv_d4", out)

    def test_name_prefix_is_not_a_reference(self):
        cfg = {"dies": {"qwen_kvsys": {"src": "/x/src_kv_d10"}}}
        out = A.select(["src_kv_d1", "src_kv_d10"], cfg, [json.dumps(cfg), "", ""], {"src_kv_d1": 1, "src_kv_d10": 9})
        self.assertEqual(out, [])                                 # d1 is the only older tree = the rollback; d10 is not a reference to d1
        self.assertEqual(A.ref_count("src_kv_d1", [json.dumps(cfg)]), 0)

    def test_unknown_die_unreferenced_is_a_candidate(self):
        out = A.select(["src_other_x"], {"dies": {}}, ["", "", ""], {"src_other_x": 1})
        self.assertEqual(out, ["src_other_x"])


class Run(unittest.TestCase):
    def test_dry_run_deletes_nothing_and_apply_stops_at_target_with_df_in_log(self):
        root = mk([("src_kv_a", 500), ("src_kv_b", 400), ("src_kv_c", 300), ("src_kv_d", 200), ("src_kv_e", 100)])
        cfg = {"dies": {"qwen_kvsys": {"src": "/x/src_kv_e"}}}; texts = [json.dumps(cfg), "", ""]
        log = []
        r = A.run(root, cfg, texts, set(), lambda t: None, log.append, 350, apply=False, free=lambda: 100.0)
        self.assertTrue(all(x["result"] == "WOULD-DELETE" for x in r)); self.assertEqual(sorted(os.listdir(root)), ["src_kv_a", "src_kv_b", "src_kv_c", "src_kv_d", "src_kv_e"])
        state = {"f": 100.0}
        def dele(p):
            import shutil; shutil.rmtree(p); state["f"] += 120.0
        r = A.run(root, cfg, texts, set(), lambda t: None, log.append, 350, apply=True, delete=dele, free=lambda: state["f"])
        done = [x for x in r if x.get("result") == "DELETED"]
        self.assertEqual(len(done), 3)                            # 100 -> 460 after 3 deletes >= 350: stop; a-c deleted, d kept as the rollback
        self.assertEqual(sorted(os.listdir(root)), ["src_kv_d", "src_kv_e"])
        self.assertTrue(all("free_before" in x and "free_after" in x for x in done))

    def test_guard_refusal_and_unstored_signed_unit_refuse(self):
        root = mk([("src_kv_a", 500), ("src_kv_b", 400), ("src_kv_c", 300), ("src_kv_e", 100)])        # c = the one rollback
        os.makedirs(os.path.join(root, "src_kv_a", "u")); open(os.path.join(root, "src_kv_a", "u", "signoff.json"), "w").write(json.dumps({"verdict": "SIGNED"}))
        old = time.time() - 500; os.utime(os.path.join(root, "src_kv_a"), (old, old))              # creating u/ bumped the mtime
        cfg = {"dies": {"qwen_kvsys": {"src": "/x/src_kv_e"}}}
        r = A.run(root, cfg, [json.dumps(cfg), "", ""], set(), lambda t: "protected" if t.endswith("src_kv_b") else None, lambda x: None, 999, apply=True, free=lambda: 1.0)
        res = {os.path.basename(x["tree"]): x["result"] for x in r if "tree" in x}
        self.assertIn("SIGNED unit", res["src_kv_a"]); self.assertTrue(os.path.exists(os.path.join(root, "src_kv_a")))
        self.assertTrue(res["src_kv_b"].startswith("REFUSED: protected")); self.assertNotIn("src_kv_c", res)
