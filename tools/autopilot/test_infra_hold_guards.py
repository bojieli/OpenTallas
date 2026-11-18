"""WAVE-PILOT-FIX 11-17 (COORD FABLE-FLOW-1900 C, D): host-environment fails are INFRA with the host in the key; a preflight cannot close the breaker;
a hold release term changes only with its cause."""
import copy, sys, unittest, unittest.mock
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import flow_guard as FG  # noqa: E402
import kit_wave as KW  # noqa: E402
import kit_wave_edit as KE  # noqa: E402


class HostInfra(unittest.TestCase):
    WHYS = ["docker: Error response from daemon: No such image: opentallas/orfs:asap7lock-grtoff",
            "KIT_NOT_SELF_CONTAINED: kit recipe must copy the file into the kit at staging @place: /home/ubuntu/.local/bin/ot-job-docker",
            "OSError: [Errno 28] No space left on device"]

    def test_classified_infra_and_never_a_design_fail(self):
        for w in self.WHYS:
            cls, _ = KW.classify("place", w)
            self.assertEqual(cls, "INFRA", w)
            self.assertTrue(KW.is_host_fail("INFRA", w), w)                       # no same-fail-key refusal, retries elsewhere

    def test_a_design_failure_is_still_not_infra(self):
        cls, _ = KW.classify("place", "KIT_PREFLIGHT FAIL issues 4 duplicate_modules")
        self.assertNotEqual(cls, "INFRA")

    def test_infra_key_carries_the_host(self):
        why = self.WHYS[0]
        a = KW.infra_key({"dies": {"qwen_kvsys": {}}}, {"die": "qwen_kvsys", "item": "x", "gen_host": "epyc7", "block_sha": "b"}, "INFRA", why)
        b = KW.infra_key({"dies": {"qwen_kvsys": {}}}, {"die": "qwen_kvsys", "item": "x", "gen_host": "epyc8", "block_sha": "b"}, "INFRA", why)
        self.assertNotEqual(a, b)                                                 # the same fail on another host is a new key
        c = KW.infra_key({"dies": {"qwen_kvsys": {}}}, {"die": "qwen_kvsys", "item": "x", "gen_host": "epyc7", "block_sha": "b"}, "INFRA", why)
        self.assertEqual(a, c)


class BreakerNeedsAProbe(unittest.TestCase):
    KEY = "CLASS s81|place|FLOW: kit recipe / preflight"

    def st(self):
        return {"flow_guard": {"open": {self.KEY: {"die": "s81", "kind": "pf", "state": "shut", "t": 1.0, "last_fail": 1.0, "fams": ["a"], "probe": {}}},
                               "last": {"s81/a__t1": self.KEY}, "last2": {}, "probation": {}, "fails": [], "pf_posted": {}, "paths": {}, "trees": {}, "refused": []}}

    def test_a_passing_preflight_opens_the_probe_window_and_closes_nothing(self):
        st = self.st()
        rel = FG.release_by_preflight(st, {self.KEY: [True, True]}, now=5.0)
        self.assertTrue(rel and "PROBE" in rel[0][1])
        self.assertIn(self.KEY, st["flow_guard"]["open"])
        self.assertEqual(st["flow_guard"]["open"][self.KEY]["state"], "probe")

    def test_only_a_probe_passing_closes_it(self):
        st = self.st()
        FG.release_by_preflight(st, {self.KEY: [True]}, now=5.0)
        self.assertEqual(FG.held_key(st, "s81", "a__t1", claim=True), "")         # the probe launches
        self.assertIn(self.KEY, st["flow_guard"]["open"])
        FG.probe_result(st, "s81", "a__t1", "place", passed=True)
        self.assertNotIn(self.KEY, st["flow_guard"]["open"])


class HoldReleaseTerms(unittest.TestCase):
    def doc(self, n=5):
        return {"dies": {"qwen_compute": {"hold_records": [
            {"id": f"r{i}", "plan_sha": "p", "reason": "st_a fix is in N2B", "release": ["event_adopt:N2B", "lint_clean:qwen_compute"], "keys": [f"k{i}"]} for i in range(n)]}}}

    def repoint(self, doc, upto, because=False):
        new = copy.deepcopy(doc)
        for r in new["dies"]["qwen_compute"]["hold_records"][:upto]:
            r["release"] = ["event_adopt:N1B", "lint_clean:qwen_compute"]
            if because:
                r["release_changed_because"] = f"{r['id']}: cause moved"
        return new

    def test_bulk_repoint_without_a_cause_is_refused(self):
        old = self.doc()
        errs = KE.release_repoint_errors(old, self.repoint(old, 5), [])
        self.assertTrue(errs and any("release_changed_because" in e for e in errs))

    def test_bulk_repoint_to_one_event_is_refused_even_with_reasons(self):
        old = self.doc()
        errs = KE.release_repoint_errors(old, self.repoint(old, 5, because=True), [])
        self.assertTrue(any("bulk re-point refused" in e for e in errs))

    def test_a_single_record_with_a_named_cause_change_is_allowed(self):
        old = self.doc()
        self.assertEqual(KE.release_repoint_errors(old, self.repoint(old, 1, because=True), []), [])

    def test_an_unrelated_edit_is_not_touched(self):
        old = self.doc()
        new = copy.deepcopy(old)
        new["dies"]["qwen_compute"]["hold_records"][0]["reason"] = "reworded"
        self.assertEqual(KE.release_repoint_errors(old, new, []), [])


class CompareAndSwap(unittest.TestCase):
    """COORD 17:5x: kit_wave_edit wrote the whole file from a base older than HEAD and reverted another lane's commit."""

    def setUp(self):
        import json, subprocess, tempfile
        self.json = json
        self.d = tempfile.mkdtemp()
        self.g = lambda *a: subprocess.run(["git", "-C", self.d, "-c", "user.name=t", "-c", "user.email=t@t", *a], check=True, capture_output=True, text=True)
        self.g("init", "-q")
        (Path(self.d) / "autopilot").mkdir()
        self.f = Path(self.d) / "autopilot/kit_wave.json"
        self.base = {"enabled": True, "max_inflight": 5, "dies": {"s81": {"hold_records": [{"id": "h", "release": ["event_adopt:A"]}]}}}
        self.f.write_text(KE.dump(self.base))
        self.g("add", "-A"); self.g("commit", "-q", "-m", "init")

    def other_lane_commit(self, mutate):
        doc = self.json.loads(self.g("show", "HEAD:autopilot/kit_wave.json").stdout)
        mutate(doc)
        mine = self.f.read_text()
        self.f.write_text(KE.dump(doc)); self.g("add", "--", "autopilot/kit_wave.json"); self.g("commit", "-q", "-m", "other lane")
        return mine

    def head(self):
        return self.json.loads(self.g("show", "HEAD:autopilot/kit_wave.json").stdout)

    def commit(self, msg, rel):
        self.g("add", "--", rel); self.g("commit", "-q", "-m", msg)

    def test_head_moving_before_the_commit_rebases_the_patch(self):
        real = KE.release_repoint_errors
        moved = []

        def hook(old, new, ops):
            if not moved:                                                       # another lane commits while the patch is computed
                moved.append(1)
                self.other_lane_commit(lambda doc: doc["dies"]["s81"]["hold_records"][0]["release"].append("tree_has:r620"))
            return real(old, new, ops)
        with unittest.mock.patch.object(KE, "release_repoint_errors", hook):
            KE.edit(self.d, [{"op": "replace", "path": "/max_inflight", "value": 9}], "mine", commit_cmd=self.commit)
        h = self.head()
        self.assertEqual(h["max_inflight"], 9)
        self.assertEqual(h["dies"]["s81"]["hold_records"][0]["release"], ["event_adopt:A", "tree_has:r620"])   # the other lane's term survives

    def test_a_commit_slipping_in_during_the_commit_is_repaired(self):
        state = []

        def commit(msg, rel):
            if not state:                                                       # coord-commit waited on its lock; the other lane commits first
                state.append(1)
                mine = self.other_lane_commit(lambda doc: doc["dies"]["s81"]["hold_records"][0]["release"].append("tree_has:r620"))
                self.f.write_text(mine)                                         # ... then our stale full file is committed over it
            self.commit(msg, rel)
        KE.edit(self.d, [{"op": "replace", "path": "/max_inflight", "value": 9}], "mine", commit_cmd=commit)
        h = self.head()
        self.assertEqual(h["max_inflight"], 9)
        self.assertEqual(h["dies"]["s81"]["hold_records"][0]["release"], ["event_adopt:A", "tree_has:r620"])

    def test_an_uncommitted_edit_by_someone_else_is_never_overwritten(self):
        self.f.write_text(KE.dump(dict(self.base, max_inflight=77)))            # a dirty working file
        with self.assertRaises(SystemExit):
            KE.edit(self.d, [{"op": "replace", "path": "/enabled", "value": False}], "mine", commit_cmd=self.commit)
        self.assertEqual(self.json.loads(self.f.read_text())["max_inflight"], 77)


class StaleFailEntries(unittest.TestCase):
    """COORD: four QC items never relaunched on N1B because fail_keys / fail_sigs still held their event-L2 failures."""

    def cfg(self):
        return {"dies": {"qwen_compute": {"event": "N1B"}, "s81": {"event": "E1"}}}

    def st(self):
        return {"items": {"a": {"die": "qwen_compute", "item": "slw_fw_v1", "event": "L2", "status": "FAIL", "updated": 5.0},
                          "b": {"die": "qwen_compute", "item": "slw_hc1", "event": "N1B", "status": "FAIL", "updated": 5.0}},
                "fail_keys": {"qwen_compute|slw_fw_v1": {"key": "k", "n": 2},                       # old entry: event from the latest FAIL row (L2)
                              "qwen_compute|slw_hc1": {"key": "k2", "n": 1},                        # failure on the current event: kept
                              "qwen_compute|x": {"key": "k3", "event": "L2"},                       # event recorded in the entry
                              "s81|y": {"key": "k4", "event": "E1"}},
                "fail_sigs": {"qwen_compute|slw_fw_v1": {"attempts": ["L2@11", "L2@12"], "n": 2},
                              "qwen_compute|slw_hc1": {"attempts": ["L2@11", "N1B@12"], "n": 2},      # includes the current event: kept
                              "s81|y": {"attempts": ["E1@3"]}}}

    def test_entries_of_an_old_event_are_dropped_and_current_ones_kept(self):
        st = self.st()
        self.assertEqual(KW.prune_stale_fail_entries(self.cfg(), st), (2, 1))
        self.assertEqual(sorted(st["fail_keys"]), ["qwen_compute|slw_hc1", "s81|y"])
        self.assertEqual(sorted(st["fail_sigs"]), ["qwen_compute|slw_hc1", "s81|y"])

    def test_idempotent_and_safe_without_state(self):
        st = self.st()
        KW.prune_stale_fail_entries(self.cfg(), st)
        self.assertEqual(KW.prune_stale_fail_entries(self.cfg(), st), (0, 0))
        self.assertEqual(KW.prune_stale_fail_entries({"dies": {}}, {}), (0, 0))

    def test_a_new_fail_key_records_its_event(self):
        import tempfile
        st, cfg = {"items": {}}, {"dies": {"qwen_compute": {"event": "N1B", "src": "", "plan": ""}}}
        rec = {"die": "qwen_compute", "item": "z", "event": "N1B", "stage": "gen", "dir": tempfile.mkdtemp()}
        KW.note_fail_key(cfg, st, rec, "FLOW", "unclassified failure @gen (see log): x")
        self.assertEqual(st["fail_keys"]["qwen_compute|z"]["event"], "N1B")


class SyncBackoff(unittest.TestCase):
    """COORD FABLE-FLOW-2200 E: a QC file sync to epyc2 failed every 2 min (epyc2 root full): back off by (host, path)."""

    def run_tick(self, rc, now):
        import tempfile
        cfg = {"dies": {"qwen_compute": {"gen_hosts": ["intel1", "epyc8"]}},
               "_item_incomplete": {"epyc2": {"qwen_compute": {"a": "/srv/opentallas-scratch2/claude/x/bind_L2 missing", "b": "/srv/opentallas-scratch2/claude/x/bind_L2 missing"}},
                                    "intel1": {"qwen_compute": {}}}}
        runs = []
        ap = type("AP", (), {"log": staticmethod(lambda m: None)})()
        with unittest.mock.patch.object(KW.time, "sleep"), unittest.mock.patch.object(KW.time, "time", return_value=now), \
                unittest.mock.patch.object(KW, "_heal_path", return_value=self.path):
            done = KW.sync_item_inputs(ap, cfg, run=lambda argv, inp=None: runs.append(1) or rc)
        return runs, done

    def setUp(self):
        import tempfile
        self.path = str(Path(tempfile.mkdtemp()) / "heal.json")

    def test_a_failing_host_path_is_not_retried_every_tick(self):
        runs, _ = self.run_tick(2, 10_000.0)
        first = len(runs)
        self.assertGreaterEqual(first, 1)
        self.assertEqual(len(self.run_tick(2, 10_120.0)[0]), 0)             # 2 min later: backed off (items a and b share the host + path)
        self.assertEqual(len(self.run_tick(2, 10_000.0 + 400)[0]), first)    # after 5 min it tries once more
        self.assertEqual(len(self.run_tick(2, 10_400.0 + 300)[0]), 0)        # the next wait doubles (10 min)

    def test_success_clears_the_backoff(self):
        self.run_tick(2, 10_000.0)
        self.assertGreaterEqual(len(self.run_tick(0, 10_400.0)[0]), 1)
        self.assertGreaterEqual(len(self.run_tick(0, 10_401.0)[0]), 0)


class UnreachableHoldAtAdopt(unittest.TestCase):
    def test_a_hold_on_an_event_that_does_not_exist_is_dropped_and_a_real_one_kept(self):
        import hold_records as HR
        plan = "p" * 64
        cfg = {"_now": 1000.0, "dies": {"s81": {"event": "EVT9", "plan_sha256": plan, "planned_events": ["EVT10"],
               "hold_event_items": {plan: ["a", "b"]},
               "hold_records": [{"id": "dead", "plan_sha": plan, "reason": "x", "release": ["event_adopt:EVT1"], "keys": ["a"], "migrated": True},
                                {"id": "live", "plan_sha": plan, "reason": "y", "release": ["event_adopt:EVT10"], "keys": ["b"], "migrated": True}]}}}
        HR.compile_holds(cfg)
        self.assertEqual(list(cfg["dies"]["s81"]["hold_items"]), ["b"])


class OrphanStopAndDriftOwner(unittest.TestCase):
    def test_orphan_stop_is_live_by_default_and_opt_out_is_log_only(self):
        seen = []

        class FakeWJ:
            @staticmethod
            def orphan_scopes(sh, hub, rows, dry, cap):
                seen.append(dry)
                return {"epyc8": {"orphans": [{"unit": "u1", "age_h": 1.7, "why": "older attempt of a replaced row"}]}}
        st = {"items": {"a": {"die": "s81", "event": "E", "item": "x", "attempt": 1, "started": KW.time.time(), "status": "RUNNING"},
                        "b": {"die": "s81", "event": "E", "item": "x", "attempt": 2, "started": KW.time.time(), "status": "RUNNING"}}}
        ap = type("AP", (), {"DRY": False, "HUB_NAME": "hub", "sh": staticmethod(lambda *a, **k: (0, "", "")), "log": staticmethod(lambda m: None)})()
        with unittest.mock.patch.object(KW, "WJ", FakeWJ):
            self.assertEqual(KW.orphan_sweep(ap, {}, st), 1)
            self.assertEqual(KW.orphan_sweep(ap, {"orphan_sweep_live": False}, st), 1)
            self.assertEqual(KW.orphan_sweep(ap, {"orphan_sweep": False}, st), 0)
        self.assertEqual(seen, [False, True])                                   # live by default (dry False); option false = dry

    def test_drift_alert_names_the_die_owner(self):
        import json as _j, tempfile
        coord = Path(tempfile.mkdtemp())
        (coord / "autopilot").mkdir()
        work = _j.dumps({"dies": {"s81": {"x": 2}, "qwen_kvsys": {"y": 1}}}).encode()
        orig = _j.dumps({"dies": {"s81": {"x": 1}, "qwen_kvsys": {"y": 1}}}).encode()
        (coord / KW.CFG_REL).write_bytes(work)
        out = []
        ap = type("AP", (), {"COORD": str(coord), "log": staticmethod(lambda m: None), "coord_append": staticmethod(lambda f, line: out.append(line))})()
        cfg = {"dies": {"s81": {"die_owner": "S81-DIE-R3"}, "qwen_kvsys": {"die_owner": "KV-R3"}}}
        st = {}
        KW.config_drift(ap, st, now=100.0, read_origin=lambda: orig, cfg=cfg)
        KW.config_drift(ap, st, now=200.0, read_origin=lambda: orig, cfg=cfg)   # second tick: alert
        self.assertEqual(len(out), 1)
        self.assertIn("-> COORD, S81-DIE-R3]", out[0])
        self.assertIn("die(s) s81", out[0])
        self.assertNotIn("KV-R3", out[0])                                       # the die that did not drift is not addressed

    def test_lock_take_waits_blocking_and_gets_it_when_released(self):
        import subprocess, tempfile, time as _t
        p = Path(tempfile.mkdtemp()) / "l.lock"
        holder = subprocess.Popen([sys.executable, "-c", "import fcntl,time,sys;f=open(sys.argv[1],'a+');fcntl.flock(f,fcntl.LOCK_EX);print('held',flush=True);time.sleep(2)", str(p)],
                                  stdout=subprocess.PIPE, text=True)
        holder.stdout.readline()
        t0 = _t.time()
        lk = KW.lock_take(p, wait_s=20)
        self.assertIsNotNone(lk)
        self.assertLess(_t.time() - t0, 6)                                      # woke when the holder released, not after a 5 s poll cycle
        lk.close()
        holder.wait()

    def test_lock_take_times_out_when_held(self):
        import subprocess, tempfile
        p = Path(tempfile.mkdtemp()) / "l.lock"
        holder = subprocess.Popen([sys.executable, "-c", "import fcntl,time,sys;f=open(sys.argv[1],'a+');fcntl.flock(f,fcntl.LOCK_EX);print('held',flush=True);time.sleep(5)", str(p)],
                                  stdout=subprocess.PIPE, text=True)
        holder.stdout.readline()
        self.assertIsNone(KW.lock_take(p, wait_s=1))
        holder.terminate()
        holder.wait()


class DieToolErrorsAndDedupe(unittest.TestCase):
    TB = ('Traceback (most recent call last):\n  File "/srv/x/tools/die_plan/bind.py", line 10, in kit_rtl\n    raise\n'
          'ValueError: reference net u_a/b not structurally mapped\n')

    def test_a_die_tool_value_error_is_flow_with_the_message(self):
        cls, why = KW.classify("kit_rtl", self.TB)
        self.assertEqual(cls, "FLOW")
        self.assertIn("reference net u_a/b not structurally mapped", why)
        cls2, _ = KW.classify("gen", self.TB.replace("ValueError", "KeyError"))
        self.assertEqual(cls2, "FLOW")

    def test_other_python_exceptions_and_foreign_tracebacks_stay_as_before(self):
        cls, _ = KW.classify("kit_rtl", self.TB.replace("ValueError", "AttributeError"))
        self.assertEqual(cls, "INFRA")                                                  # tool skew: unchanged
        cls, _ = KW.classify("kit_rtl", "Traceback (most recent call last):\n  File \"/usr/lib/x.py\", line 1\nValueError: boom\n")
        self.assertNotEqual(cls, "FLOW")                                                # not raised in a die tool: no change here

    def test_dedupe_ignores_cancelled_and_infra_owners(self):
        self.assertTrue(KW.dedup_owner_not_a_verdict({"status": "CANCELLED"}))
        self.assertTrue(KW.dedup_owner_not_a_verdict({"status": "FAIL", "class": "INFRA"}))
        self.assertTrue(KW.dedup_owner_not_a_verdict({"status": "ENQUEUED", "q_status": "FAIL", "q_class": "INFRA"}))
        self.assertFalse(KW.dedup_owner_not_a_verdict({"status": "FAIL", "class": "FLOW"}))
        self.assertFalse(KW.dedup_owner_not_a_verdict(None))


class RemovedKeyClassClose(unittest.TestCase):
    KEY = "CLASS s81|place|FLOW: tool / Tcl error @place: Error: <id>.tcl, N OT_VPW_BANK needs exactly two real VP SRAM macros, got N"

    def setUp(self):
        self.st = {"flow_guard": {"open": {self.KEY: {"die": "s81", "state": "probe", "kind": "", "n": 9, "fams": ["col"], "probe": {}}},
                                  "last": {"s81/col_x": self.KEY}, "last2": {"s81/col_x": self.KEY}, "probation": {}, "fails": [], "pf_posted": {}, "paths": {}, "trees": {}, "refused": []}}
        self.ap = type("AP", (), {"log": staticmethod(lambda m: None)})()

    def test_class_closes_when_its_config_key_is_removed(self):
        cfg = {"dies": {"s81": {"gen_env": {"OT_S81_VPW_BANK": "1"}}}}
        KW.note_class_cfg_keys(cfg, self.st, "s81", "col_x")
        self.assertEqual(self.st["flow_guard"]["open"][self.KEY]["cfg_keys"], ["OT_VPW_BANK"])
        self.assertEqual(KW.close_removed_key_classes(self.ap, cfg, self.st), [])        # key still set: stays open
        cfg["dies"]["s81"]["gen_env"] = {}                                                  # r687: the marker is removed
        self.assertEqual(len(KW.close_removed_key_classes(self.ap, cfg, self.st)), 1)
        self.assertNotIn(self.KEY, self.st["flow_guard"]["open"])

    def test_a_class_whose_token_was_never_a_config_key_is_not_touched(self):
        cfg = {"dies": {"s81": {"gen_env": {}}}}
        KW.note_class_cfg_keys(cfg, self.st, "s81", "col_x")
        self.assertEqual(self.st["flow_guard"]["open"][self.KEY]["cfg_keys"], [])
        self.assertEqual(KW.close_removed_key_classes(self.ap, cfg, self.st), [])
        self.assertIn(self.KEY, self.st["flow_guard"]["open"])


if __name__ == "__main__":
    unittest.main()
