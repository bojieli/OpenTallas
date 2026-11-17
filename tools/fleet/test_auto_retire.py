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


class RetirementQueueRefs(unittest.TestCase):
    def setUp(self):
        self.trees = ["src_kv_d1", "src_kv_d2", "src_kv_d3", "src_kv_d4"]
        self.mt = {name: i for i, name in enumerate(self.trees, 1)}
        self.old = "/x/kw45/src_kv_d1"
        self.cfg = {"dies": {"qwen_kvsys": {"src": "/x/kw45/src_kv_d4",
                                           "superseded_trees": [self.old]}}}

    def select(self, cfg=None, texts=None):
        cfg = self.cfg if cfg is None else cfg
        return A.select(self.trees, cfg, [json.dumps(cfg), "", ""] if texts is None else texts, self.mt)

    def test_queue_only_is_eligible_without_mutating_inputs(self):
        before = json.dumps(self.cfg)
        texts = [before, "", ""]
        self.assertIn("src_kv_d1", self.select(texts=texts))
        self.assertEqual(json.dumps(self.cfg), before)
        self.assertEqual(texts, [before, "", ""])

    def test_same_path_current_rollback_or_other_config_still_protects(self):
        import copy
        for key in ("src", "rollback_tree", "manual_protected"):
            cfg = copy.deepcopy(self.cfg)
            cfg["dies"]["qwen_kvsys"][key] = self.old
            self.assertNotIn("src_kv_d1", self.select(cfg), key)
        cfg = copy.deepcopy(self.cfg)
        cfg["dies"]["qwen_kvsys"]["item_inputs"] = {"x": {"superseded_trees": [self.old]}}
        self.assertNotIn("src_kv_d1", self.select(cfg))

    def test_state_marker_and_malformed_or_mismatched_config_still_protect(self):
        for texts in ([json.dumps(self.cfg), self.old, ""], [json.dumps(self.cfg), "", self.old],
                      [json.dumps(self.cfg)+" extra", "", ""],
                      [json.dumps(dict(self.cfg, other="different")), "", ""]):
            self.assertNotIn("src_kv_d1", self.select(texts=texts))
        cfg = {"dies": {"qwen_kvsys": {"src": "/x/kw45/src_kv_d4", "superseded_trees": {"path": self.old}}}}
        self.assertNotIn("src_kv_d1", self.select(cfg))

    def test_run_recheck_ignores_queue_but_not_signed_store_or_guard(self):
        root = mk([("src_kv_a", 500), ("src_kv_b", 400), ("src_kv_c", 100)])
        self.addCleanup(__import__("shutil").rmtree, root)
        old = os.path.join(root, "src_kv_a")
        cfg = {"dies": {"qwen_kvsys": {"src": os.path.join(root, "src_kv_c"),
                                      "superseded_trees": [old]}}}
        texts = [json.dumps(cfg), "", ""]
        def run(refuse=lambda _: None):
            return A.run(root, cfg, texts, set(), refuse, lambda _: None, 999, free=lambda: 1.0)
        self.assertEqual(run()[0]["result"], "WOULD-DELETE")
        self.assertIn("protected", run(lambda _: "protected manual/live")[0]["result"])
        os.makedirs(os.path.join(old, "unit"))
        with open(os.path.join(old, "unit/signoff.json"), "w") as f:
            json.dump({"verdict": "SIGNED"}, f)
        now = time.time()
        os.utime(old, (now-500, now-500))
        self.assertIn("SIGNED unit", run()[0]["result"])
        self.assertTrue(os.path.isdir(old))
