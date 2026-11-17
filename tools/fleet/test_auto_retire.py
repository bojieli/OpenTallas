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


class ExplicitRollback(unittest.TestCase):
    def setUp(self):
        self.root = mk([("src_head_d1", 500), ("src_head_d2", 400), ("src_head_d3", 300),
                        ("src_head_d4", 200), ("src_head_d5", 100)])
        self.addCleanup(__import__("shutil").rmtree, self.root)
        self.names = os.listdir(self.root)
        self.mt = {n: os.lstat(os.path.join(self.root, n)).st_mtime for n in self.names}
        self.row = {"src": os.path.join(self.root, "src_head_d4"),
                    "rollback_tree": os.path.join(self.root, "src_head_d3"),
                    "superseded_trees": [os.path.join(self.root, "src_head_d2")]}

    def select(self, row=None, extra="", texts=None):
        cfg = {"dies": {"s81_head": self.row if row is None else row}}
        return A.select(self.names, cfg, [json.dumps(cfg), extra, ""] if texts is None else texts, self.mt, root=self.root)

    def test_existing_explicit_rollback_does_not_reserve_an_extra_tree(self):
        self.assertEqual(self.select(), ["src_head_d1", "src_head_d2"])
        # Canonical rollback remains protected even when there is no textual ref.
        self.assertNotIn("src_head_d3", self.select(texts=["", "", ""]))

    def test_missing_wrong_die_newer_and_symlink_rollback_keep_fallback(self):
        for path in (os.path.join(self.root, "src_head_missing"),
                     os.path.join(self.root, "src_head_d5"),
                     os.path.join(self.root, "src_kv_other")):
            self.assertNotIn("src_head_d3", self.select(dict(self.row, rollback_tree=path)))
        no = dict(self.row); no.pop("rollback_tree")
        self.assertNotIn("src_head_d3", self.select(no))
        alias = os.path.join(self.root, "alias")
        os.symlink(self.row["rollback_tree"], alias)
        self.assertNotIn("src_head_d3", self.select(dict(self.row, rollback_tree=alias)))

    def test_same_name_elsewhere_does_not_qualify_and_other_refs_still_protect(self):
        with tempfile.TemporaryDirectory() as td:
            other = os.path.join(td, "src_head_d3"); os.mkdir(other)
            self.assertIsNone(A.rollback_snapshot("s81_head", dict(self.row, rollback_tree=other),
                                                  "src_head_d4", self.names, self.mt, root=self.root))
        self.assertNotIn("src_head_d2", self.select(extra=os.path.join(self.root, "src_head_d2")))
        row = dict(self.row, manual_protected=os.path.join(self.root, "src_head_d2"))
        self.assertNotIn("src_head_d2", self.select(row))
        self.assertNotIn("src_head_d5", self.select())  # pending newer adoption


class LiveState(unittest.TestCase):
    STATE = json.dumps({"items": {
        "a": {"status": "CANCELLED", "kit": "/x/kw45/src_kv_d1/k"}, "b": {"status": "FAIL", "src": "/x/kw45/src_kv_d2"},
        "c": {"status": "RUNNING", "src": "/x/kw45/src_kv_d3"}, "d": {"status": "ENQUEUED", "src": "/x/kw45/src_kv_d4"}}})

    def test_finished_attempts_do_not_keep_a_tree_live_ones_do(self):
        trees = ["src_kv_d1", "src_kv_d2", "src_kv_d3", "src_kv_d4", "src_kv_d5", "src_kv_d6"]
        mt = {t: 10 * (i + 1) for i, t in enumerate(trees)}
        cfg = {"dies": {"qwen_kvsys": {"src": "/x/kw45/src_kv_d6"}}}
        out = A.select(trees, cfg, [json.dumps(cfg), self.STATE, ""], mt)
        self.assertEqual(out, ["src_kv_d1", "src_kv_d2"])        # d3 running, d4 queued: kept; d5 = the one rollback; d1/d2 only named by CANCELLED / FAIL rows

    def test_unknown_state_shape_is_kept_whole(self):
        self.assertEqual(A.live_state_text("not json /x/src_kv_d1"), "not json /x/src_kv_d1")
        self.assertEqual(A.live_state_text(json.dumps({"rows": []})), json.dumps({"rows": []}))
        self.assertEqual(A.ref_count("src_kv_d1", [A.live_state_text(self.STATE)]), 0)
        self.assertEqual(A.ref_count("src_kv_d4", [A.live_state_text(self.STATE)]), 1)
