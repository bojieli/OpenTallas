import copy, json, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hold_records as HR  # noqa: E402
import kit_wave as KW  # noqa: E402

PLAN = "p" * 64


def base():
    return {"dies": {"s81": {"event": "B6gG3", "plan": "/x/B6gG3.json", "plan_sha256": PLAN, "planned_events": ["B6gG3b"],
                             "hold_event_items": {PLAN: ["col_a__t1", "col_a__t2", "col_b__t1", "ser_x"]}},
                     "hbm": {"event": "pEv11c", "plan_sha256": "h" * 64}}}


def rec(**k):
    r = {"id": "r1", "plan_sha": PLAN, "reason": "why", "release": ["event_adopt:B6gG3b"], "patterns": ["col_a__*"]}
    r.update(k)
    return r


class T(unittest.TestCase):
    def test_add_expands_pattern_on_compile(self):
        c = base()
        HR.add_record(c, "s81", rec())
        HR.compile_holds(c)
        self.assertEqual(list(c["dies"]["s81"]["hold_items"]), ["col_a__t1", "col_a__t2"])
        self.assertEqual(c["_hold_compiled"]["s81"]["col_a__t1"], "r1")

    def test_rejects_unknown_event_lane_and_free_text(self):
        for term in ("event_adopt:B6gG1d", "event_adopt:Event F", "lane_ready:HEAD-99", "lint_clean:nodie", "kit_snap:zz",
                     "input_staged:rel/x", "digest_changed:x", "event_adopt:B6*"):
            with self.assertRaises(ValueError, msg=term):
                HR.add_record(base(), "s81", rec(release=[term]))

    def test_rejects_zero_match_unbound_and_empty(self):
        for bad in (rec(patterns=["nope*"]), rec(plan_sha=""), rec(patterns=[], items=[]), rec(reason="")):
            with self.assertRaises(ValueError):
                HR.add_record(base(), "s81", bad)

    def test_event_release_when_adopted(self):
        c = base()
        HR.add_record(c, "s81", rec())
        c["dies"]["s81"]["event"] = "B6gG3b"
        c["dies"]["s81"]["plan"] = "/x/B6gG3b.json"
        HR.compile_holds(c, HR.Ctx(event_met=KW._hold_term_met))
        self.assertEqual(c["dies"]["s81"]["hold_items"], {})
        self.assertEqual(len(c["_hold_auto_released"]), 2)

    def test_lint_clean_is_per_item(self):
        c = base()
        HR.add_record(c, "s81", rec(release=["lint_clean:s81"]))
        c["dies"]["s81"]["_lint_clean"] = ["col_a__t1"]
        HR.compile_holds(c)
        self.assertEqual(list(c["dies"]["s81"]["hold_items"]), ["col_a__t2"])
        HR.compile_holds(c, HR.Ctx(lint_fn=lambda die, item: item != "col_a__t2"))      # live path: a known sdc_lint failure holds, the rest releases
        self.assertEqual(list(c["dies"]["s81"]["hold_items"]), ["col_a__t2"])
        c["dies"]["s81"]["hold_items"] = {}
        HR.compile_holds(c, HR.Ctx(lint_fn=lambda die, item: True))
        self.assertEqual(c["dies"]["s81"]["hold_items"], {})

    def test_digest_changed_and_staged_and_snap(self):
        c = base()
        HR.add_record(c, "s81", rec(release=["digest_changed"], digest="aaa"))
        HR.compile_holds(c, HR.Ctx(digest_fn=lambda cfg, die: "aaa"))
        self.assertEqual(len(c["dies"]["s81"]["hold_items"]), 2)
        c["dies"]["s81"]["hold_items"] = {}
        HR.compile_holds(c, HR.Ctx(digest_fn=lambda cfg, die: "bbb"))
        self.assertEqual(c["dies"]["s81"]["hold_items"], {})
        c = base()
        HR.add_record(c, "s81", rec(release=["input_staged:/a/b", "kit_snap:hbm"]))
        HR.compile_holds(c, HR.Ctx(exists_fn=lambda p: True, kit_snap_fn=lambda cfg, die: False))
        self.assertEqual(len(c["dies"]["s81"]["hold_items"]), 2)           # all terms must be met
        c["dies"]["s81"]["hold_items"] = {}
        HR.compile_holds(c, HR.Ctx(exists_fn=lambda p: True, kit_snap_fn=lambda cfg, die: True))
        self.assertEqual(c["dies"]["s81"]["hold_items"], {})

    def test_plan_sha_move_supersedes_or_follows(self):
        c = base()
        HR.add_record(c, "s81", rec())
        HR.add_record(c, "s81", rec(id="r2", patterns=["ser_*"], follow_plan=True))
        d = c["dies"]["s81"]
        d["plan_sha256"] = "n" * 64
        d["hold_event_items"]["n" * 64] = ["ser_x", "ser_y", "col_a__t1"]
        HR.compile_holds(c)
        self.assertEqual(sorted(d["hold_items"]), ["col_a__t1", "col_a__t2", "ser_x", "ser_y"])   # r1 keeps its old items, r2 rebound
        got = {(f["code"], f["id"]) for f in HR.audit(c)}
        self.assertIn(("HOLD-SUPERSEDED", "r1"), got)
        self.assertNotIn(("HOLD-SUPERSEDED", "r2"), got)

    def test_audit_unreachable_and_held_but_launched(self):
        c = base()
        c["dies"]["s81"]["hold_items"] = {"col_a__*": "old", "ser_x": "old2"}
        c["dies"]["s81"]["hold_release_on"] = {"col_a__*": "event_adopt:Event F", "ser_x": "lane_ready:X"}
        HR.migrate_cfg(c)
        HR.compile_holds(c)
        f = HR.audit(c, [("s81", "col_a__t9"), ("s81", "zzz")])
        codes = [(x["code"], x["n"]) for x in f]
        self.assertEqual(sorted(x["code"] for x in f), ["HELD-BUT-LAUNCHED", "TERM-UNREACHABLE", "TERM-UNREACHABLE"])
        self.assertEqual([x["items"] for x in f if x["code"] == "HELD-BUT-LAUNCHED"], [["col_a__t9"]])

    def test_migrate_keeps_effective_holds(self):
        c = base()
        d = c["dies"]["s81"]
        d["hold_items"] = {"a": "r1", "b": "r1", "c*": "r2", "d": "r1"}
        d["hold_release_on"] = {"a": "event_adopt:B6gG3", "b": "event_adopt:B6gG3", "c*": "lane_result:X + merge:abc", "zz": "merge:q"}
        old = KW.load_config(json.dumps(c))
        HR.migrate_cfg(c)
        self.assertEqual(len(c["dies"]["s81"]["hold_records"]), 3)
        new = KW.load_config(json.dumps(c))
        self.assertEqual(list(new["dies"]["s81"]["hold_items"].items()), list(old["dies"]["s81"]["hold_items"].items()))
        self.assertEqual(sorted(old["_hold_auto_released"]), sorted(new["_hold_auto_released"]))

    def test_convert_retypes_and_reports_unmapped(self):
        c = base()
        c["dies"]["s81"]["hold_items"] = {"a": "r", "b": "q"}
        c["dies"]["s81"]["hold_release_on"] = {"a": "event_adopt:B6gG3* (x) + lane_result:sdc_lint 0", "b": "lane_ready:Z"}
        HR.migrate_cfg(c)
        done, left = HR.convert_cfg(c, {"event_adopt:B6gG3* (x) + lane_result:sdc_lint 0": ["event_adopt:B6gG3b", "lint_clean:s81"]},
                                    {"s81": ["B6gG3c"]})
        self.assertEqual((done, [x[2] for x in left]), (1, ["lane_ready:Z"]))
        self.assertIn("b6gg3c", HR.known_events(c["dies"]["s81"]))
        with self.assertRaises(ValueError):
            HR.convert_cfg(c, {"lane_ready:Z": ["event_adopt:Nope1"]})

    def test_proof_and_census_terms(self):
        c = base()
        d = c["dies"]["s81"]
        for bad in ("proof:", "proof:a b", "census_lt:abc", "census_lt:"):
            with self.assertRaises(ValueError, msg=bad):
                HR.add_record(c, "s81", rec(release=[bad]))
        HR.add_record(c, "s81", rec(release=["proof:DRT0255", "census_lt:400k"]))
        HR.compile_holds(c, HR.Ctx(proof_fn=lambda n: n == "DRT0255", cells_fn=lambda die, i: 300000 if i == "col_a__t1" else 500000))
        self.assertEqual(list(d["hold_items"]), ["col_a__t2"])
        HR.compile_holds(c, HR.Ctx(proof_fn=lambda n: False, cells_fn=lambda die, i: 1))     # recompile is idempotent, proof unmet
        self.assertEqual(sorted(d["hold_items"]), ["col_a__t1", "col_a__t2"])
        HR.compile_holds(c, HR.Ctx(proof_fn=lambda n: True))                                 # cells unknown = held
        self.assertEqual(sorted(d["hold_items"]), ["col_a__t1", "col_a__t2"])

    def test_convert_keys_splits_records_and_drops(self):
        c = base()
        d = c["dies"]["s81"]
        d["hold_items"] = {"a": "r", "b": "r", "c": "r", "keep": "r"}
        d["hold_release_on"] = {k: "lane_ready:X" for k in d["hold_items"]}
        HR.migrate_cfg(c, only=["s81"])
        HR.convert_cfg(c, {}, {"s81": ["KV-HG1"]})
        self.assertEqual(HR.convert_keys(c, {"s81": {"a": ["event_adopt:KV-HG1"], "b": ["event_adopt:KV-HG1"], "c": None}}), (2, 1))
        HR.compile_holds(c)
        self.assertEqual(sorted(d["hold_items"]), ["a", "b", "keep"])
        self.assertEqual(sorted(r["id"] for r in d["hold_records"]), ["s81-mig-001", "s81-mig-001-k1"])
        with self.assertRaises(ValueError):
            HR.convert_keys(c, {"s81": {"zz": None}})
        with self.assertRaises(ValueError):
            HR.convert_keys(c, {"s81": {"keep": ["event_adopt:Nope1"]}})

    def test_migrate_only_one_die(self):
        c = base()
        c["dies"]["s81"]["hold_items"] = {"a": "r"}
        c["dies"]["hbm"]["hold_items"] = {"z": "r"}
        HR.migrate_cfg(c, only=["s81"])
        self.assertEqual(c["dies"]["hbm"]["hold_items"], {"z": "r"})
        self.assertNotIn("hold_records", c["dies"]["hbm"])

    def test_event_prefix_glob(self):
        c = base()
        HR.add_record(c, "s81", rec(release=["event_adopt:B6gG3*"]))                      # matches planned B6gG3b / current B6gG3
        with self.assertRaises(ValueError):
            HR.add_record(c, "s81", rec(release=["event_adopt:B6gX*"]))                    # no such event
        with self.assertRaises(ValueError):
            HR.add_record(c, "s81", rec(release=["event_adopt:B6*g3"]))
        d = c["dies"]["s81"]
        d["event"], d["plan"] = "x", "/x/zz_B6gG3b.json"
        HR.compile_holds(c, HR.Ctx(event_met=KW._hold_term_met))
        self.assertEqual(d["hold_items"], {})

    def test_tree_ready_term_validate_release_and_switch(self):
        c = base()
        d = c["dies"]["s81"]
        d.update(src="/old", die_gen_env={"A": "1"}, kit_rtl={"bind_out": "/o", "keep": 1})
        for bad in ("tree_ready:hbm:/t", "tree_ready:s81:rel/t", "tree_ready:s81:/t/", "tree_ready:s81:/a/../t", "tree_ready:s81"):
            with self.assertRaises(ValueError, msg=bad):
                HR.add_record(c, "s81", rec(release=[bad]))
        HR.add_record(c, "s81", rec(release=["tree_ready:s81:/t/src1", "lint_clean:s81"]))
        marker = {"tree": "/t/src1", "manifest_hash": "abc", "die_gen_env": {"B": "2"}, "config": {"kit_rtl": {"bind_out": "/n"}, "tools_sha": "e59"}}
        ready = {"v": False}
        ctx = HR.Ctx(tree_fn=lambda die, p: ready["v"] and p == "/t/src1", marker_fn=lambda die: marker)
        HR.compile_holds(c, ctx)
        self.assertEqual(len(d["hold_items"]), 2)
        self.assertEqual(HR.apply_tree_switches(c, ctx), [])
        self.assertEqual(d["src"], "/old")
        ready["v"] = True
        d["_lint_clean"] = ["*"]
        HR.compile_holds(c, ctx)
        self.assertEqual(d["hold_items"], {})                                    # tree ready + lint clean releases
        sw = HR.apply_tree_switches(c, ctx)
        self.assertEqual(sw[0][:2], ("s81", "/t/src1"))
        self.assertEqual((d["src"], d["src_manifest_hash"], d["die_gen_env"], d["kit_rtl"], d["tools_sha"]),
                         ("/t/src1", "abc", {"A": "1", "B": "2"}, {"bind_out": "/n", "keep": 1}, "e59"))
        self.assertEqual(HR.apply_tree_switches(c, ctx), [])                     # idempotent: nothing changes the second tick

    def test_kit_wave_tree_gate_and_switch(self):
        import tempfile, os
        calls = []
        old_fn, old_sync = KW._src_manifest_hosts, KW._TREE_SYNC
        KW._TREE_SYNC = True
        KW._src_manifest_hosts = lambda hosts, tree, expect, links_only: (calls.append((tuple(hosts), links_only, expect)) or (0, "ok"))
        try:
            with tempfile.TemporaryDirectory() as td:
                tree = os.path.join(td, "src1")
                os.makedirs(tree)
                marker = {"tree": tree, "manifest_hash": "h1", "smoke": "PASS", "die_gen_env": {"OT_PGCAP": "1"}}

                class AP:
                    HUB_NAME = "hub"
                    text = json.dumps(marker)
                    logs = []

                    @staticmethod
                    def read_coord(rel):
                        return AP.text if rel.endswith("tree_switch_s81.json") else ""

                    @staticmethod
                    def log(m):
                        AP.logs.append(m)
                c = base()
                c["hosts"] = ["epyc9"]
                c["dies"]["s81"]["gen_hosts"] = ["localhost"]                       # the die's own gen hosts win over cfg hosts
                c["dies"]["s81"]["src"] = "/old"
                HR.add_record(c, "s81", rec(release=[f"tree_ready:s81:{tree}"]))
                KW._TREE_CACHE.clear()
                tf, mf = KW.tree_gate(AP, c)
                self.assertFalse(tf("s81", tree))                                    # hash file missing on the host
                self.assertEqual(calls, [])
                KW._TREE_CACHE.clear()
                open(os.path.join(tree, ".src-manifest.sha256"), "w").write("h1\n")
                self.assertTrue(tf("s81", tree))                                     # switch time: full verify with --expect
                self.assertEqual(calls, [(("localhost",), False, "h1")])
                self.assertTrue(tf("s81", tree))
                self.assertEqual(len(calls), 1)                                      # cached: no second verify within 600 s
                next(iter(KW._TREE_CACHE.values()))["links_t"] -= 700
                self.assertTrue(tf("s81", tree))                                     # later tick: --links-only
                self.assertEqual(calls[-1], (("localhost",), True, "h1"))
                KW._src_manifest_hosts = lambda hosts, tree, expect, links_only: (1, "NOT-READY 3 files share an inode")
                next(iter(KW._TREE_CACHE.values()))["links_t"] -= 700
                self.assertFalse(tf("s81", tree))                                    # shared inodes turn the tree not-ready
                self.assertTrue(any("FAILED" in m for m in AP.logs))
                KW._src_manifest_hosts = lambda hosts, tree, expect, links_only: (0, "ok")
                KW._TREE_CACHE.clear()
                AP.text = json.dumps(dict(marker, smoke="FAIL"))
                self.assertFalse(tf("s81", tree))                                    # smoke not PASS
                AP.text = json.dumps(dict(marker, tree="/other"))
                self.assertFalse(tf("s81", tree))                                    # marker names another tree
                AP.text = json.dumps(marker)
                KW._TREE_CACHE.clear()
                KW.compile_hold_records(c, lambda r: False, tf, mf)
                self.assertEqual(c["dies"]["s81"]["hold_items"], {})
                sw = HR.apply_tree_switches(c, KW.hold_ctx(c, lambda r: False, tf, mf))
                self.assertEqual((c["dies"]["s81"]["src"], c["dies"]["s81"]["die_gen_env"]), (tree, {"OT_PGCAP": "1"}))
                self.assertEqual(sw[0][1], tree)
        finally:
            KW._src_manifest_hosts, KW._TREE_SYNC = old_fn, old_sync

    def test_published_d6_switch_refreshes_source_identity_not_pinned_attempt(self):
        import tempfile, os
        from unittest.mock import patch
        main = "41bb1dcfd10a88b78ac6296e8209d8783422fcae"
        old = "7073a6b4a599c1de9e041896421b3b779045df1d"
        with tempfile.TemporaryDirectory() as td:
            tree = Path(td) / "src_s81_pin_41bb1dcfd10a_d6"
            tree.mkdir()
            (tree / ".src-manifest.sha256").write_text("hash-d6\n")
            (tree / ".src-manifest.json").write_text(json.dumps(dict(main_sha=main, manifest_hash="hash-d6")))
            attempt = Path(td) / "attempt"
            attempt.mkdir()
            spec = attempt / "spec.json"
            pinned = json.dumps(dict(src_sha=old, queue_src="main@" + old, src="/old/G3b/src"))
            spec.write_text(pinned)
            marker = dict(tree=str(tree), src_manifest_sha="hash-d6", smoke="PASS", tools_sha="f" * 40,
                          _validated_main_sha="a" * 40, config={"tools_sha": "f" * 40})
            class AP:
                HUB_NAME = "hub"
                read_coord = staticmethod(lambda rel: json.dumps(marker))
                log = staticmethod(lambda text: None)
            c = base()
            d = c["dies"]["s81"]
            d.update(src=str(tree), src_sha=old, queue_src="main@" + old, gen_hosts=["localhost"])
            HR.add_record(c, "s81", rec(release=["tree_ready:s81:" + str(tree)]))
            with patch.object(KW, "_TREE_CACHE", {}), patch.object(KW, "_TREE_SYNC", True), \
                 patch.object(KW, "_src_manifest_hosts", return_value=(0, "verified")):
                tf, mf = KW.tree_gate(AP, c)
                ctx = KW.hold_ctx(c, lambda ref: False, tf, mf)
                changed = HR.apply_tree_switches(c, ctx)
                self.assertEqual((d["src_sha"], d["queue_src"], d["tools_sha"]), (main, "main@" + main, "f" * 40))
                self.assertIn("src_sha", changed[0][2])
                self.assertEqual(HR.apply_tree_switches(c, ctx), [])
                self.assertEqual(spec.read_text(), pinned)

    def test_switched_plan_carries_only_explicit_marker_declaration(self):
        import tempfile, hashlib
        with tempfile.TemporaryDirectory() as td:
            old, new = Path(td) / "old.json", Path(td) / "B6gF2s3.json"
            old.write_text('{"event":"F2s2"}\\n')
            new.write_text('{"event":"F2s3"}\\n')
            old_sha = hashlib.sha256(old.read_bytes()).hexdigest()
            new_sha = hashlib.sha256(new.read_bytes()).hexdigest()
            for declared in (None, new_sha):
                with self.subTest(marker_declaration=declared):
                    c = base()
                    d = c["dies"]["s81"]
                    d.update(plan=str(old), plan_sha256=old_sha)
                    HR.add_record(c, "s81", rec(release=["tree_ready:s81:/published"]))
                    marker = dict(tree="/published", plan=str(new), config={"plan": str(new)})
                    if declared:
                        marker["plan_sha256"] = declared
                    ctx = HR.Ctx(tree_fn=lambda die, path: True, marker_fn=lambda die: marker)
                    HR.apply_tree_switches(c, ctx)
                    self.assertEqual(d["plan"], str(new))
                    self.assertEqual(d["plan_sha256"], declared or old_sha)
                    mismatch = KW.plan_sha_mismatch(d, {"plan_sha": new_sha})
                    if declared:
                        self.assertIsNone(mismatch)
                    else:
                        self.assertIn("PLAN_SHA_MISMATCH", mismatch)
                    self.assertEqual(HR.apply_tree_switches(c, ctx), [])

    def test_tree_switch_honors_explicit_config_plan_declaration(self):
        c = base()
        HR.add_record(c, "s81", rec(release=["tree_ready:s81:/published"]))
        marker = dict(tree="/published", plan_sha256="a" * 64,
                      config={"plan": "/explicit/plan.json", "plan_sha256": "b" * 64})
        ctx = HR.Ctx(tree_fn=lambda die, path: True, marker_fn=lambda die: marker)
        HR.apply_tree_switches(c, ctx)
        self.assertEqual(c["dies"]["s81"]["plan_sha256"], "b" * 64)

    def test_tree_switch_honors_explicit_source_identity_after_validation(self):
        c = base()
        HR.add_record(c, "s81", rec(release=["tree_ready:s81:/published"]))
        explicit = {"src_sha": "b" * 40, "queue_src": "claude/composed@" + "b" * 40}
        marker = dict(tree="/published", _validated_main_sha="a" * 40, config=explicit)
        ctx = HR.Ctx(tree_fn=lambda die, path: True, marker_fn=lambda die: marker)
        HR.apply_tree_switches(c, ctx)
        self.assertEqual({k:c["dies"]["s81"][k] for k in explicit}, explicit)

    def test_unverified_tree_metadata_never_changes_source_identity(self):
        import tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as td:
            tree = Path(td) / "candidate"
            tree.mkdir()
            (tree / ".src-manifest.sha256").write_text("h1\n")
            (tree / ".src-manifest.json").write_text(json.dumps(dict(main_sha="a" * 40)))
            marker = dict(tree=str(tree), manifest_hash="h1", smoke="PASS", _validated_main_sha="c" * 40)
            class AP:
                HUB_NAME = "hub"
                read_coord = staticmethod(lambda rel: json.dumps(marker))
                log = staticmethod(lambda text: None)
            c = base()
            d = c["dies"]["s81"]
            d.update(src="/old", src_sha="b" * 40, queue_src="main@" + "b" * 40, gen_hosts=["localhost"])
            HR.add_record(c, "s81", rec(release=["tree_ready:s81:" + str(tree)]))
            with patch.object(KW, "_TREE_CACHE", {}), patch.object(KW, "_TREE_SYNC", True), \
                 patch.object(KW, "_src_manifest_hosts", return_value=(1, "manifest drift")):
                tf, mf = KW.tree_gate(AP, c)
                self.assertEqual(HR.apply_tree_switches(c, KW.hold_ctx(c, lambda ref: False, tf, mf)), [])
                self.assertEqual(d["src_sha"], "b" * 40)
                self.assertNotIn("_validated_main_sha", mf("s81"))

    def test_switch_only_record_holds_nothing_and_switches(self):
        c = base()
        d = c["dies"]["hbm"]
        d["src"] = "/old"
        r = {"id": "sw1", "plan_sha": "h" * 64, "reason": "switch", "release": ["tree_ready:hbm:/t/h1"], "switch_only": True}
        for bad in (dict(r, items=["x"]), dict(r, release=["digest_changed"]), dict(r, release=["tree_ready:s81:/t/h1"])):
            with self.assertRaises(ValueError):
                HR.add_record(c, "hbm", bad)
        HR.add_record(c, "hbm", r)
        ctx = HR.Ctx(tree_fn=lambda die, p: p == "/t/h1", marker_fn=lambda die: {"manifest_hash": "m"})
        HR.compile_holds(c, ctx)
        self.assertEqual(d["hold_items"], {})
        self.assertEqual([x for x in HR.audit(c) if x["code"] in ("HOLD-ZERO-MATCH", "TERM-UNREACHABLE")], [])
        self.assertEqual(HR.apply_tree_switches(c, ctx)[0][:2], ("hbm", "/t/h1"))
        self.assertEqual(d["src"], "/t/h1")
        HR.convert_keys(c, {"hbm": {}})                                           # pruning keeps a switch_only record
        self.assertEqual(len(d["hold_records"]), 1)

    def test_route_record_compiles_into_route_hold_items(self):
        c = base()
        d = c["dies"]["s81"]
        d["route_hold_items"] = {"keep": "legacy"}
        HR.add_record(c, "s81", rec(id="rt1", route=True, patterns=[], items=["col_a__t1"], release=["event_adopt:B6gG3b"]))
        HR.compile_holds(c)
        self.assertEqual(d["route_hold_items"], {"keep": "legacy", "col_a__t1": "why"})
        self.assertEqual(d["hold_items"], {})
        HR.compile_holds(c)                                                          # idempotent
        self.assertEqual(len(d["route_hold_items"]), 2)
        d["event"], d["plan"] = "B6gG3b", "/x/B6gG3b.json"
        HR.compile_holds(c, HR.Ctx(event_met=KW._hold_term_met))
        self.assertEqual(d["route_hold_items"], {"keep": "legacy"})                   # released, legacy key untouched

    def test_proof_record_never_holds_its_proof_items(self):
        c = base()
        d = c["dies"]["s81"]
        d["proof_items"] = {"DRT0255": ["col_a__t1", "ser_x"]}
        with self.assertRaises(ValueError):
            HR.add_record(c, "s81", rec(release=["proof:DRT0255"], patterns=[], items=["ser_x"]))
        HR.add_record(c, "s81", rec(release=["proof:DRT0255"], patterns=["col_a__*"], items=["col_b__t1"]))
        HR.compile_holds(c)
        self.assertEqual(sorted(d["hold_items"]), ["col_a__t2", "col_b__t1"])            # col_a__t1 (the proof) carved out
        self.assertEqual(HR.audit(c), [])
        # a migrated glob key that covers a proof item is expanded against the item list, minus the proof items
        c = base()
        d = c["dies"]["s81"]
        d["proof_items"] = {"DRT0255": ["col_a__t1"]}
        d["hold_items"] = {"col_a__*": "r", "other": "r"}
        d["hold_release_on"] = {"col_a__*": "proof:DRT0255", "other": "proof:DRT0255"}
        HR.migrate_cfg(c)
        c["_item_names"] = {"s81": ["col_a__t1", "col_a__t2", "zz"]}
        HR.compile_holds(c)
        self.assertEqual(sorted(d["hold_items"]), ["col_a__t2", "other"])
        del c["_item_names"]
        HR.compile_holds(c)                                                           # no item list: pattern kept, audit names it
        self.assertEqual(sorted(HR.summarize(HR.audit(c)).items()), [("PROOF-HELD", 1)])

    def test_record_is_authority_over_written_back_file_keys_and_legacy_audit(self):
        c = base()
        d = c["dies"]["s81"]
        HR.add_record(c, "s81", rec(release=["event_adopt:B6gG3b"]))
        d["hold_items"] = {"col_a__t1": "stale prose copy", "loose_key": "prose with no record"}
        d["event"], d["plan"] = "B6gG3b", "/x/B6gG3b.json"
        HR.compile_holds(c, HR.Ctx(event_met=KW._hold_term_met))
        self.assertEqual(d["hold_items"], {"loose_key": "prose with no record"})        # released key not kept alive by its file copy
        self.assertEqual([(x["code"], x["n"]) for x in HR.audit(c)], [("LEGACY-HOLD", 1)])

    def test_kit_wave_lint_clean_item(self):
        c = {"_lint_fail": {"s81": {"col_a__t1"}}}
        self.assertFalse(KW.lint_clean_item(c, "s81", "col_a__t1"))
        self.assertTrue(KW.lint_clean_item(c, "s81", "col_b__t1"))
        self.assertFalse(KW.lint_clean_item(c, "s81", "col_a__*"))                       # a glob key is clean only if no covered item failed
        self.assertTrue(KW.lint_clean_item(c, "hbm", "x"))

    def test_result_term_and_its_proof_items(self):
        c = base()
        d = c["dies"]["s81"]
        d["proof_items"] = {"svc-ready": ["col_a__t1"]}
        for bad in ("result:svc-ready", "result::x", "result:LANE:a b", "result:LANE:"):
            with self.assertRaises(ValueError, msg=bad):
                HR.add_record(c, "s81", rec(release=[bad]))
        HR.add_record(c, "s81", rec(release=["result:SVC-LANE:svc-ready"], patterns=["col_*"]))
        HR.compile_holds(c)
        self.assertEqual(sorted(d["hold_items"]), ["col_a__t2", "col_b__t1"])             # the pilot (proof item) is not held
        HR.compile_holds(c, HR.Ctx(result_fn=lambda lane, tag: (lane, tag) == ("SVC-LANE", "svc-ready")))
        self.assertEqual(d["hold_items"], {})

    def test_kit_wave_result_fn(self):
        lines = ["- 2026-11-16 08:00 PST RESULT [SVC-LANE -> COORD] svc-ready PASS: 16/16 closure applied",
                 "- 2026-11-16 08:01 PST RESULT [OTHER-LANE -> COORD] svc-ready PASS",
                 "- 2026-11-16 08:02 PST RESULT [SVC-LANE -> COORD] other-tag PASS",
                 "- 2026-11-16 08:03 PST RESULT [SVC-LANE -> COORD] svc-ready NOT yet, FAIL"]
        f = KW.result_pass_fn(lines)
        self.assertTrue(f("SVC-LANE", "svc-ready"))
        self.assertTrue(f("OTHER-LANE", "svc-ready"))
        self.assertFalse(f("SVC-LANE", "svc-ready-2"))
        self.assertFalse(KW.result_pass_fn(lines[2:])("SVC-LANE", "svc-ready"))
        self.assertFalse(KW.result_pass_fn([lines[0].replace("-> COORD]", "-> COORD; cc SVC-LANE]").replace("[SVC-LANE", "[X")])("SVC-LANE", "svc-ready"))

    def test_instruction_text_in_a_ruling_is_not_a_result(self):
        ruling = ("- 2026-11-16 07:00 PST RULING [COORD -> MERGE-QUEUE-1, FABLE-FIX-S81-SVC] r297: FABLE-FIX-S81-SVC: post exactly "
                  "RESULT [FABLE-FIX-S81-SVC -> COORD] svc-ready PASS: <evidence> when ready; HEAD-SERDES-O proves head-serdes-fanout PASS later")
        ready = "- 2026-11-16 06:59 PST READY [HOLDGEN-1115 -> COORD] a RESULT [LANE -> x] line with tag PASS releases"
        real = "- 2026-11-16 09:00 PST RESULT [FABLE-FIX-S81-SVC -> COORD] svc-ready PASS: closure ref_1116 applied 16/16"
        self.assertFalse(KW.result_pass_fn([ruling, ready])("FABLE-FIX-S81-SVC", "svc-ready"))
        self.assertFalse(KW.proof_pass_fn(KW.result_posts([ruling, ready]))("head-serdes-fanout"))
        self.assertTrue(KW.result_pass_fn([ruling, real])("FABLE-FIX-S81-SVC", "svc-ready"))
        self.assertTrue(KW.result_pass_fn(["  - 2026-11-16 09:00 UTC RESULT [FABLE-FIX-S81-SVC -> COORD] svc-ready: PASS"])("FABLE-FIX-S81-SVC", "svc-ready"))
        rp = "- 2026-11-16 09:01 PST RESULT [HEAD-SERDES-O -> COORD] head-serdes-fanout PASS: gate TT -30"
        self.assertTrue(KW.proof_pass_fn(KW.result_posts([rp]))("head-serdes-fanout"))
        self.assertFalse(KW.proof_pass_fn(KW.result_posts([rp]))("head-serdes"))


if __name__ == "__main__":
    unittest.main()
