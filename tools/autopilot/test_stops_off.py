"""WAVE-PILOT-FIX 11-18 (OWNER order via COORD: remove all safety stops): with cfg stops_off no hold record, class breaker, dedupe hold, pilot gate, retry probe or
tree-switch marker blocks a launch.  Infra rails (ot-run admission, disk floor, delete guard, OOM) are not touched."""
import sys, unittest
import unittest.mock
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import flow_guard as FG  # noqa: E402
import hold_records as HR  # noqa: E402
import kit_wave as KW  # noqa: E402
import plan_block_identity as BI  # noqa: E402

PLAN = "p" * 64


def cfg(off):
    c = {"dies": {"s81": {"event": "E1", "plan": "/x/E1.json", "plan_sha256": PLAN, "hold_event_items": {PLAN: ["a", "b", "c"]},
                          "hold_records": [{"id": "r", "plan_sha": PLAN, "reason": "x", "release": ["event_adopt:E2"], "keys": ["a", "b"], "migrated": True},
                                           {"id": "p", "plan_sha": PLAN, "reason": "pilot", "release": ["gen_pilot:s81:aaaaaaaaaaaa"], "items": ["*"],
                                            "pilot_items": ["c"], "auto_pilot": True}]}}}
    if off:
        c["stops_off"] = True
    return c


class StopsOff(unittest.TestCase):
    def test_holds_hold_without_the_option_and_nothing_with_it(self):
        on = cfg(False)
        HR.compile_holds(on)
        self.assertTrue(on["dies"]["s81"]["hold_items"])
        off = cfg(True)
        HR.compile_holds(off)
        self.assertEqual(off["dies"]["s81"].get("hold_items") or {}, {})
        self.assertEqual(off["_hold_rec_info"], {})

    def test_no_tree_switch_pilot_marker(self):
        c = cfg(True)
        d = c["dies"]["s81"]
        d["src_manifest_hash"] = "c" * 64
        c["_item_names"] = {"s81": ["a", "b", "c"]}
        self.assertFalse(HR.add_pilot_hold(c, "s81", d, {}))
        c2 = cfg(False)
        c2["dies"]["s81"]["hold_records"] = []
        c2["dies"]["s81"]["src_manifest_hash"] = "c" * 64
        c2["_item_names"] = {"s81": ["a", "b", "c"]}
        self.assertTrue(HR.add_pilot_hold(c2, "s81", c2["dies"]["s81"], {}))

    def test_retry_probe_never_defers(self):
        st = {"items": {f"k{i}": {"die": "s81", "item": f"i{i}", "attempt": 4, "status": "FAIL", "started": 1.0} for i in range(8)}}
        on, off = {"dies": {"s81": {"event": "e"}}}, {"dies": {"s81": {"event": "e"}}, "stops_off": True}
        for i in range(8):
            st["items"][f"r{i}"] = {"die": "s81", "item": "z", "attempt": 5 + i, "status": "RUNNING", "started": KW.time.time() + i}
        self.assertTrue(KW.retry_probe_defer(on, st, "s81", {"item": "i0"}))
        self.assertEqual(KW.retry_probe_defer(off, st, "s81", {"item": "i0"}), "")

    def test_a_class_breaker_does_not_hold_a_launch(self):
        st = {}
        for i in range(5):
            FG.record_fail(st, "s81", f"it{i}", "FLOW", "timing closure failed @place: x", now=1000 + i, legacy=False, stage="place")
        self.assertTrue(FG.held_key(st, "s81", "it0"))                           # the breaker itself still opens and records
        ap = type("AP", (), {"DRY": True, "HUB_NAME": "hub", "log": staticmethod(lambda m: None), "AP_DIR": "/tmp"})()
        for off in (False, True):
            c = {"dies": {"s81": {"event": "E", "gen_host": "h", "gen_hosts": ["h"]}}}
            if off:
                c["stops_off"] = True
            logs = []
            ap.log = logs.append
            try:
                KW.launch(ap, c, {"items": {}, "flow_guard": st["flow_guard"]}, "s81", {"item": "it0", "kind": "type"}, "hub")
            except Exception:
                pass                                                              # launch needs a real plan; only the HELD line matters here
            held = any("LAUNCH-HELD" in m for m in logs)
            self.assertEqual(held, not off)

    def test_dedupe_hold_is_skipped(self):
        owner = {"die": "s81", "item": "o", "status": "FAIL", "q_status": None, "attempt": 3, "updated": 5.0, "class": "FLOW"}
        st = {"items": {"o": owner}, "dedup_released": {"s81|m": {"owner": "o", "sig": "FAIL/None/3"}}, "flow_guard": {"open": {}, "last": {}, "last2": {}}}
        ap = type("AP", (), {"DRY": True, "HUB_NAME": "hub", "AP_DIR": "/tmp"})()
        for off in (False, True):
            logs = []
            ap.log = logs.append
            c = {"dies": {"s81": {"event": "E", "gen_host": "h", "gen_hosts": ["h"]}}}
            if off:
                c["stops_off"] = True
            try:
                with unittest.mock.patch.object(KW, "dedup_group", lambda *a: "s81|m"):      # S81-COL-FLOW-1118: dedup is opt-in; this item is a member
                    KW.launch(ap, c, dict(st, dedup_released={"s81|m": {"owner": "o", "sig": "FAIL/None/3"}}), "s81", {"item": "m", "kind": "type"}, "hub")
            except Exception:
                pass
            self.assertEqual(any("DEDUP terminal" in m for m in logs), not off)


class HbmIsExcluded(unittest.TestCase):
    def test_helper(self):
        self.assertFalse(FG.stops_off_die({}, "s81"))
        self.assertTrue(FG.stops_off_die({"stops_off": True}, "s81"))
        self.assertFalse(FG.stops_off_die({"stops_off": True}, "hbm"))
        self.assertTrue(FG.stops_off_die({"stops_off": True, "stops_off_exclude": []}, "hbm"))
        self.assertFalse(FG.stops_off_die({"stops_off": True, "stops_off_exclude": ["hbm", "qwen_kvsys"]}, "qwen_kvsys"))

    def test_hbm_hold_records_still_hold_and_the_others_do_not(self):
        c = cfg(True)
        d = c["dies"]["s81"]
        c["dies"]["hbm"] = {"event": "E1", "plan": "/x/E1.json", "plan_sha256": PLAN, "hold_event_items": {PLAN: ["a", "b", "c"]},
                            "hold_records": [{"id": "h", "plan_sha": PLAN, "reason": "parked", "release": ["event_adopt:E2"], "keys": ["a"], "migrated": True}]}
        HR.compile_holds(c)
        self.assertEqual(d.get("hold_items") or {}, {})
        self.assertEqual(list(c["dies"]["hbm"]["hold_items"]), ["a"])

    def test_hbm_launches_still_obey_the_breaker_and_pilot_markers(self):
        c = cfg(True)
        c["dies"]["hbm"] = {"event": "E1"}
        st = {}
        for i in range(5):
            FG.record_fail(st, "hbm", f"it{i}", "FLOW", "timing closure failed @place: x", now=1000 + i, legacy=False, stage="place")
        self.assertTrue(FG.held_key(st, "hbm", "it0"))
        c["dies"]["hbm"]["src_manifest_hash"] = "c" * 64
        c["_item_names"] = {"hbm": ["a", "b"]}
        c["dies"]["hbm"].update(hold_event_items={PLAN: ["a", "b"]}, plan_sha256=PLAN)
        self.assertTrue(HR.add_pilot_hold(c, "hbm", c["dies"]["hbm"], {}))


class RepeatLinesInsteadOfRefusals(unittest.TestCase):
    """OWNER 11-18 (r704): repeat-stop and same-fail-key refusals are off under stops_off; a REPEAT line names the owner lane"""

    def run_launch(self, off):
        logs = []
        ap = type("AP", (), {"DRY": True, "HUB_NAME": "hub", "AP_DIR": "/tmp", "log": staticmethod(logs.append)})()
        c = {"dies": {"s81": {"event": "E", "gen_host": "h", "gen_hosts": ["h"], "die_owner": "S81-DIE-R3"}}}
        if off:
            c["stops_off"] = True
        st = {"items": {}, "repeat_ledger": {"s81|x": {}}, "fail_keys": {"s81|x": {"key": "k1", "n": 3, "cls": "FLOW", "stage": "gen"}}}
        orig = KW.fail_key_gate, KW.RS.gate
        KW.fail_key_gate = lambda cfg, st_, die, item, blk: (True, "same fail key k1 (FLOW @gen, x3)", [])
        KW.RS.gate = lambda *a, **k: (True, "REPEAT-STOP: same failure 3x", None)
        try:
            try:
                KW.launch(ap, c, st, "s81", {"item": "x", "kind": "type"}, "hub")
            except Exception:
                pass                                                  # past the gates launch needs a real plan; only the gate lines matter
        finally:
            KW.fail_key_gate, KW.RS.gate = orig
        return logs

    def test_refused_without_the_option(self):
        logs = self.run_launch(False)
        self.assertTrue(any("LAUNCH-HELD" in m and "REPEAT-STOP" in m for m in logs))
        self.assertFalse(any("KIT-WAVE REPEAT " in m for m in logs))

    def test_logged_not_refused_with_the_option(self):
        logs = self.run_launch(True)
        rep = [m for m in logs if "KIT-WAVE REPEAT " in m]
        self.assertEqual(len(rep), 2)                                                 # the repeat-stop line and the fail-key line
        self.assertTrue(all("[owner S81-DIE-R3]" in m for m in rep))
        self.assertFalse(any("LAUNCH-HELD" in m or "LAUNCH-REFUSED" in m for m in logs))


class RouteHoldsAndCensus(unittest.TestCase):
    def test_owner_review_route_holds_hold_nothing_under_stops_off_except_hbm(self):
        c = {"dies": {"s81": {"route_hold_items": {"q_b1*": "KW-FIX-45 11-11 cut hold"}}, "hbm": {"route_hold_items": {"q_b1*": "KW-FIX-45 11-11 cut hold"}}}}
        for die in ("s81", "hbm"):
            rec = {"die": die, "item": "q_b102", "status": "PASS"}
            self.assertEqual(KW.route_hold_reason(c, rec), "KW-FIX-45 11-11 cut hold")
            on = dict(c, stops_off=True)
            if die == "hbm":
                self.assertEqual(KW.route_hold_reason(on, rec), "KW-FIX-45 11-11 cut hold")   # HBM is parked: stops_off never releases it
            else:
                self.assertIsNone(KW.route_hold_reason(on, rec))

    def test_signed_rows_are_not_counted_as_waiting(self):
        import under_use as UU
        items = {"a": {"die": "s81", "item": "a", "status": "ENQUEUED", "q_status": "SIGNED"},
                 "b": {"die": "s81", "item": "b", "status": "ENQUEUED", "q_status": "SIGNED-LINKED"},
                 "c": {"die": "s81", "item": "c", "status": "ENQUEUED", "q_status": "RUNNING"},
                 "d": {"die": "s81", "item": "d", "status": "ROUTE-HELD", "route_hold": "WAIT-FORM: x"}}
        cls = UU.row_classes(items, {"dies": {"s81": {}}})
        self.assertEqual(sorted(cls), ["c", "d"])
        self.assertEqual(cls["c"], "gate:q_running")


class SameInputSkip(unittest.TestCase):
    """OWNER r705 (2): skip a relaunch only on the FULL input hash of an attempt that failed in the tool (rt sha, design snapshot hash, spec digest, env keys)"""

    def cfg(self, **die):
        d = {"event": "E", "gen_host": "h", "gen_hosts": ["h"], "die_owner": "S81-DIE-R3", "src_manifest_hash": "snap1", "gen_env": {"OT_A": "1"}, "_plan_sha": "p1"}
        d.update(die)
        return {"dies": {"s81": d}, "stops_off": True}

    def test_hash_moves_with_snapshot_env_plan_and_rt(self):
        base = KW.full_input_hash(self.cfg(), "s81", "x", "blk")
        self.assertTrue(base)
        self.assertEqual(base, KW.full_input_hash(self.cfg(), "s81", "x", "blk"))
        self.assertNotEqual(base, KW.full_input_hash(self.cfg(src_manifest_hash="snap2"), "s81", "x", "blk"))
        self.assertNotEqual(base, KW.full_input_hash(self.cfg(gen_env={"OT_A": "2"}), "s81", "x", "blk"))
        self.assertNotEqual(base, KW.full_input_hash(self.cfg(), "s81", "x", "blk2"))
        old = KW._EXEC_TOOLS.copy()
        try:
            KW._EXEC_TOOLS[str(Path(KW.__file__).resolve().parents[2])] = "another-exec-digest"
            self.assertNotEqual(base, KW.full_input_hash(self.cfg(), "s81", "x", "blk"))
        finally:
            KW._EXEC_TOOLS.clear()
            KW._EXEC_TOOLS.update(old)

    def launch_logs(self, cfg, stored):
        logs = []
        ap = type("AP", (), {"DRY": True, "HUB_NAME": "hub", "AP_DIR": "/tmp", "log": staticmethod(logs.append)})()
        st = {"items": {}, "fail_keys": {"s81|x": {"key": "k", "full_hash": stored, "n": 2, "cls": "FLOW", "stage": "gen"}}}
        orig = KW.fail_key_gate
        KW.fail_key_gate = lambda *a, **k: (True, "same fail key", [])
        try:
            try:
                KW.launch(ap, cfg, st, "s81", {"item": "x", "kind": "type", "block_sha": "blk"}, "hub")
            except Exception:
                pass
        finally:
            KW.fail_key_gate = orig
        return logs

    def test_identical_full_hash_is_skipped_and_logged(self):
        c = self.cfg()
        logs = self.launch_logs(c, KW.full_input_hash(c, "s81", "x", "blk"))
        self.assertTrue(any("SKIP-SAME-INPUT" in m and "[owner S81-DIE-R3]" in m for m in logs))

    def test_any_env_snapshot_or_code_change_releases_it(self):
        old_hash = KW.full_input_hash(self.cfg(), "s81", "x", "blk")
        for c in (self.cfg(gen_env={"OT_A": "2"}), self.cfg(src_manifest_hash="snap2")):
            logs = self.launch_logs(c, old_hash)
            self.assertFalse(any("SKIP-SAME-INPUT" in m for m in logs))
            self.assertTrue(any("KIT-WAVE REPEAT" in m for m in logs))                 # still launches, with the owner REPEAT line

    def test_no_stored_hash_never_skips(self):
        logs = self.launch_logs(self.cfg(), "")
        self.assertFalse(any("SKIP-SAME-INPUT" in m for m in logs))


class CellBig(unittest.TestCase):
    """OWNER r703 (via COORD): the plan-time SPLIT-NEEDED flag (est. cells > 400k) does not block a launch under stops_off (hbm excluded)"""

    def test_plan_entry_block(self):
        d = {"_plan_flags": {"big": "split", "hard1": "hard"}}
        self.assertIn("SPLIT-NEEDED", KW.plan_entry_block(d, "big"))
        d["_stops_off"] = True
        self.assertIsNone(KW.plan_entry_block(d, "big"))
        self.assertIn("hard type", KW.plan_entry_block(d, "hard1"))                  # the other plan blocks are untouched

    def test_compile_holds_marks_the_dies(self):
        c = cfg(True)
        c["dies"]["hbm"] = {"event": "E"}
        HR.compile_holds(c)
        self.assertTrue(c["dies"]["s81"]["_stops_off"])
        self.assertFalse(c["dies"]["hbm"]["_stops_off"])

    def test_the_in_kit_cap_gets_the_owner_ruling_waiver_under_stops_off(self):
        on = {"stops_off": True, "dies": {"qwen_compute": {}, "hbm": {}}}
        self.assertEqual(KW.stops_off_cell_env(on, "qwen_compute", {"OT_X": "1"}), {"OT_X": "1", "OT_CELL_WAIVER": "r703"})
        self.assertEqual(KW.stops_off_cell_env(on, "qwen_compute", {"OT_CELL_WAIVER": "r500"}), {"OT_CELL_WAIVER": "r500"})     # a die's own ruling wins
        self.assertEqual(KW.stops_off_cell_env(on, "hbm", {}), {})                                                         # hbm excluded
        self.assertEqual(KW.stops_off_cell_env({"dies": {}}, "qwen_compute", {}), {})                                      # option off: unchanged

    def test_cell_big_line_once_per_change(self):
        logs = []
        ap = type("AP", (), {"log": staticmethod(logs.append)})()
        c = {"dies": {"qwen_compute": {"_stops_off": True, "_plan_flags": {"a": "split", "b": "split", "c": "hard"}}}}
        st = {}
        KW.cell_big_note(ap, c, st)
        KW.cell_big_note(ap, c, st)
        self.assertEqual(len([m for m in logs if "CELL-BIG" in m]), 1)
        self.assertIn("a, b", logs[0])


class FailedRowsRelaunchOnTheirOwn(unittest.TestCase):
    """COORD 11-18: S81 FAIL rows and queue-FAIL rows were never re-armed; under stops_off a failed row relaunches unless its full input hash equals the failed attempt's"""

    def row(self, **k):
        r = {"die": "s81", "item": "x", "status": "FAIL", "attempt": 3, "block_sha": "blk"}
        r.update(k)
        return r

    def cfg(self, **die):
        d = {"event": "E", "gen_host": "h", "gen_hosts": ["h"], "src_manifest_hash": "snap1", "_plan_sha": "p1"}
        d.update(die)
        return {"dies": {"s81": d}, "stops_off": True}

    def test_failed_helper(self):
        self.assertTrue(KW.so_failed(self.row()))
        self.assertTrue(KW.so_failed(self.row(status="ENQUEUED", q_status="FAIL")))
        self.assertFalse(KW.so_failed(self.row(status="ENQUEUED", q_status="RUNNING")))
        self.assertFalse(KW.so_failed(self.row(status="CANCELLED")))

    def test_same_hash_skips_other_relaunches(self):
        c = self.cfg()
        h = KW.full_input_hash(c, "s81", "x", "blk")
        self.assertTrue(KW.so_same_input(c, "s81", {"item": "x", "block_sha": "blk"}, self.row(full_hash=h)))
        self.assertFalse(KW.so_same_input(self.cfg(src_manifest_hash="snap2"), "s81", {"item": "x", "block_sha": "blk"}, self.row(full_hash=h)))   # a code / plan / env change releases it
        self.assertFalse(KW.so_same_input(c, "s81", {"item": "x", "block_sha": "blk"}, self.row()))                                                 # no stored hash: relaunches once


class ExecToolsDigest(unittest.TestCase):
    """COORD 11-18: the tools part of the input hash covers only the files a kit executes; an unrelated merge must not relaunch a failed row"""

    def tree(self):
        import tempfile
        r = Path(tempfile.mkdtemp())
        files = {"tools/die_plan/gen.py": "import gen_phys\n", "tools/die_plan/gen_phys.py": "X = 'staged_tool.py'\nY = 'run_step.tcl'\n",
                 "tools/die_plan/core_flow.py": "", "tools/die_plan/nomcap.py": "", "tools/die_plan/staged_tool.py": "a=1\n", "tools/die_plan/run_step.tcl": "puts a\n",
                 "tools/die_plan/hook.sh": "echo a\n", "tools/die_plan/nomcap_libs/a.lib.gz": "LIB1", "physical/common_flow/clock.tcl": "puts c\n",
                 "tools/autopilot/kit_rtl_post.d/s.sh": "true\n", "tools/autopilot/kit_rtl_closure.py": "z=1\n",
                 # not executed by a kit:
                 "tools/die_plan/test_gen.py": "t=1\n", "tools/die_plan/other_planner.py": "p=1\n", "tools/die_plan/README.md": "doc\n", "tools/die_plan/tests/t.tcl": "x\n",
                 "tools/autopilot/kit_wave.py": "w=1\n", "tools/autopilot/test_kit_wave.py": "t=1\n", "tools/fleet/ot-run": "f\n", "docs/x.md": "d\n"}
        for rel, txt in files.items():
            p = r / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(txt)
        return r

    def digest(self, r):
        KW._EXEC_TOOLS.pop(str(r), None)
        return KW.exec_tools_digest(r)

    def test_unrelated_changes_keep_the_digest(self):
        r = self.tree()
        base = self.digest(r)
        for rel in ("tools/die_plan/test_gen.py", "tools/die_plan/other_planner.py", "tools/die_plan/README.md", "tools/die_plan/tests/t.tcl",
                    "tools/autopilot/kit_wave.py", "tools/autopilot/test_kit_wave.py", "tools/fleet/ot-run", "docs/x.md"):
            (r / rel).write_text("changed\n")
            self.assertEqual(self.digest(r), base, rel)

    def test_every_executed_file_class_moves_it(self):
        for rel in ("tools/die_plan/run_step.tcl", "tools/die_plan/hook.sh", "tools/die_plan/staged_tool.py", "tools/die_plan/gen_phys.py", "physical/common_flow/clock.tcl",
                    "tools/die_plan/nomcap_libs/a.lib.gz", "tools/autopilot/kit_rtl_post.d/s.sh", "tools/autopilot/kit_rtl_closure.py"):
            r = self.tree()
            base = self.digest(r)
            (r / rel).write_text("changed\n")
            self.assertNotEqual(self.digest(r), base, rel)

    def test_a_new_tcl_moves_it(self):
        r = self.tree()
        base = self.digest(r)
        (r / "physical/common_flow/new_step.tcl").write_text("puts n\n")
        self.assertNotEqual(self.digest(r), base)

    def test_the_real_tree_digest_is_stable_and_smaller_than_the_whole_tools_tree(self):
        a, b = KW.exec_tools_digest(), KW.exec_tools_digest()
        self.assertEqual(a, b)
        files = KW.exec_tools_files()
        self.assertTrue(files)
        self.assertFalse(any(p.name.startswith("test_") for p in files))


if __name__ == "__main__":
    unittest.main()


class StaleCancel(unittest.TestCase):
    """COORD 11-18: a CANCELLED / SUPERSEDED row is not 'already in the wave'; no retry key needed"""

    def test_cancelled_rows_are_not_in_the_wave(self):
        d = {"event": "N1B"}
        self.assertTrue(KW.stale_cancel({"status": "CANCELLED", "class": "SUPERSEDED", "event": "L2"}, d))
        self.assertTrue(KW.stale_cancel({"status": "CANCELLED", "class": "INFRA", "event": "N1B"}, d))
        self.assertTrue(KW.stale_cancel({"status": "CANCELLED", "class": "HUNG", "event": "N1B"}, {}))

    def test_volume_and_live_rows_keep_their_rules(self):
        d = {"event": "N1B"}
        self.assertFalse(KW.stale_cancel({"status": "CANCELLED", "volume": "v", "event": "L2"}, d))
        self.assertFalse(KW.stale_cancel({"status": "RUNNING", "event": "L2"}, d))
        self.assertFalse(KW.stale_cancel({"status": "FAIL", "event": "L2"}, d))

    def test_select_relaunches_it_only_under_stops_off(self):
        src = open(KW.__file__).read()
        self.assertIn("(so_failed(rec) or stale_cancel(rec, d))", src)
        self.assertIn("stale_cancel(its[item_key(die, ev, c, blk(c))], d)", src)
        self.assertIn("not in retry and so_same_input(cfg, die, r, rec)", src)          # a retry key forces a relaunch past SKIP-SAME-INPUT


class StageScopedInput(unittest.TestCase):
    """COORD FABLE-FLOW-0800 class C: SKIP-SAME-INPUT compares the env of the stage that failed, not the die-wide env"""

    def cfg(self, **env):
        d = {"event": "E", "gen_host": "h", "gen_hosts": ["h"], "src_manifest_hash": "snap1", "gen_env": dict({"OT_PLACE_X": "1", "OT_CTS_Y": "1"}, **env), "_plan_sha": "p1"}
        return {"dies": {"s81": d}, "stops_off": True}

    def failed(self, cfg, stage="place"):
        return {"status": "FAIL", "stage": stage, "reason": "x", "block_sha": "blk", "input_parts": KW.input_parts(cfg, "s81", "x", "blk")}

    def run_with_scope(self, scope, old, new):
        orig = KW.stage_env_scope
        KW.stage_env_scope = lambda stage, why, root=None: scope
        try:
            return KW.so_same_input(new, "s81", {"item": "x", "block_sha": "blk"}, self.failed(old))
        finally:
            KW.stage_env_scope = orig

    def test_env_of_another_stage_does_not_rearm(self):
        self.assertTrue(self.run_with_scope("uses OT_PLACE_X only", self.cfg(), self.cfg(OT_CTS_Y="2")))

    def test_env_of_the_failing_stage_rearms(self):
        self.assertFalse(self.run_with_scope("uses OT_PLACE_X only", self.cfg(), self.cfg(OT_PLACE_X="2")))

    def test_unknown_stage_scope_means_all_env(self):
        self.assertFalse(self.run_with_scope(None, self.cfg(), self.cfg(OT_CTS_Y="2")))

    def test_snapshot_change_rearms_whatever_the_stage(self):
        new = self.cfg()
        new["dies"]["s81"]["src_manifest_hash"] = "snap2"
        self.assertFalse(self.run_with_scope("uses OT_PLACE_X only", self.cfg(), new))


class ReapProbeAsync(unittest.TestCase):
    """COORD class F: the fleet probe of REAP-DEAD runs detached; the tick reads a cache"""

    def ap(self, tmp):
        logs = []
        return type("AP", (), {"DRY": False, "HUB_NAME": "hub", "AP_DIR": tmp, "log": staticmethod(logs.append)})(), logs

    def test_no_cache_means_unreadable_and_a_background_refresh(self):
        import tempfile, subprocess
        with tempfile.TemporaryDirectory() as tmp:
            ap, logs = self.ap(tmp)
            started = []
            orig = KW.subprocess.Popen
            KW.subprocess.Popen = lambda *a, **k: started.append(a[0]) or None
            try:
                res, ts = KW.fleet_probe(ap, "live", ["/srv/a"], ["h"])
            finally:
                KW.subprocess.Popen = orig
            self.assertIsNone(res)
            self.assertEqual(len(started), 1)
            self.assertIn("probe-bg", started[0])
            self.assertTrue(any("REAP-PROBE" in m for m in logs))

    def test_fresh_cache_is_used_and_uncovered_root_is_pending(self):
        import tempfile, json as _j, time as _t
        with tempfile.TemporaryDirectory() as tmp:
            ap, logs = self.ap(tmp)
            Path(tmp, "reap_probe_live.json").write_text(_j.dumps({"ts": _t.time(), "roots": ["/srv/a"], "result": {"/srv/a": ["h:1"]}, "unreadable": []}))
            res, ts = KW.fleet_probe(ap, "live", ["/srv/a"], ["h"])
            self.assertEqual(res.get("/srv/a"), ["h:1"])
            self.assertEqual(res.unreadable, ())
            orig = KW.subprocess.Popen
            KW.subprocess.Popen = lambda *a, **k: None
            try:
                res, ts = KW.fleet_probe(ap, "live", ["/srv/a", "/srv/b"], ["h"])
            finally:
                KW.subprocess.Popen = orig
            self.assertIn("probe-pending", res.unreadable)
            self.assertNotIn("/srv/b", res)


class ExecutedFileHash(unittest.TestCase):
    """COORD FLOW-1000 (2): the stage's executed files are the stage input: a changed one relaunches, an unchanged family skips"""

    def cfg(self):
        return {"dies": {"s81": {"event": "E", "gen_host": "h", "gen_hosts": ["h"], "src_manifest_hash": "snap1", "gen_env": {}, "_plan_sha": "p1"}}, "stops_off": True}

    def run_cmp(self, stage, old_fam, new_fam):
        c = self.cfg()
        orig = KW.exec_family_digests
        KW.exec_family_digests = lambda root=None: old_fam
        rec = {"status": "FAIL", "stage": stage, "reason": "x", "block_sha": "blk", "input_parts": KW.input_parts(c, "s81", "x", "blk")}
        KW.exec_family_digests = lambda root=None: new_fam
        try:
            return KW.so_same_input(c, "s81", {"item": "x", "block_sha": "blk"}, rec)
        finally:
            KW.exec_family_digests = orig

    FAM = {"gen": "g1", "bind": "b1", "kit": "k1", "flow": "f1", "all": "a1"}

    def test_stage_families(self):
        self.assertEqual(KW.stage_family("gen"), "gen")
        self.assertEqual(KW.stage_family("kit_rtl"), "kit")
        self.assertEqual(KW.stage_family("route"), "flow")
        self.assertEqual(KW.stage_family(""), "all")

    def test_unchanged_family_skips_changed_one_relaunches(self):
        self.assertTrue(self.run_cmp("kit_rtl", self.FAM, dict(self.FAM, flow="f2", gen="g2")))      # other families moved: the kit_rtl failure is the same input
        self.assertFalse(self.run_cmp("kit_rtl", self.FAM, dict(self.FAM, kit="k2")))
        self.assertFalse(self.run_cmp("route", self.FAM, dict(self.FAM, flow="f2")))
        self.assertFalse(self.run_cmp("", self.FAM, dict(self.FAM, all="a2")))

    def test_old_format_attempt_relaunches_once(self):
        c = self.cfg()
        rec = {"status": "FAIL", "stage": "route", "reason": "x", "input_parts": {"noenv": "abc", "env": {}}}
        self.assertFalse(KW.so_same_input(c, "s81", {"item": "x", "block_sha": "blk"}, rec))


class StaleEnqueued(unittest.TestCase):
    """COORD / FLEET-OPS-R 11-18: an ENQUEUED row of a superseded event idle > 24 h whose queue job is not live is cancelled by the wave (SIGNED rows pinned ~145 GB)"""

    def cfg(self):
        return {"stops_off": True, "dies": {"s81": {"event": "NEW", "enabled": True}, "hbm": {"event": "NEW", "enabled": True}}}

    def row(self, die="s81", ev="OLD", q="SIGNED", age_h=100, status="ENQUEUED"):
        t = 1_000_000.0 - age_h * 3600
        return {"die": die, "item": "t", "event": ev, "status": status, "q_status": q, "q_signoff": True, "updated": t, "started": t}

    def run_it(self, r, cfg=None):
        st = {"items": {"k": r}}
        KW.retire_superseded_rows(None, cfg or self.cfg(), st, now=1_000_000.0)
        return st["items"]["k"]

    def test_old_signed_row_on_a_dead_event_is_cancelled(self):
        r = self.run_it(self.row())
        self.assertEqual((r["status"], r["class"], r["retire"]), ("CANCELLED", "SUPERSEDED", "stale-enqueued"))

    def test_young_live_current_event_and_hbm_rows_are_kept(self):
        self.assertEqual(self.run_it(self.row(age_h=3))["status"], "ENQUEUED")
        self.assertEqual(self.run_it(self.row(q="RUNNING"))["status"], "ENQUEUED")
        self.assertEqual(self.run_it(self.row(ev="NEW"))["status"], "ENQUEUED")
        self.assertEqual(self.run_it(self.row(die="hbm"))["status"], "ENQUEUED")
        self.assertEqual(self.run_it(self.row(status="ROUTE-HELD"))["status"], "ROUTE-HELD")


class EnvHashExcludesInjected(unittest.TestCase):
    """COORD FLOW-1400 (1): launch-injected env (OT_FLOW_TAG, OT_CELL_WAIVER) and rt-tree values are not inputs: the failed attempt spec and the config side must hash the same"""

    def test_injected_and_rt_values_are_dropped(self):
        env = {"OT_FLOW_TAG": "flow-x", "OT_CELL_WAIVER": "r703", "OT_TOOLS": "/srv/o/claude/rt/8958d3e8a4e7/tools", "OT_A": "1"}
        self.assertEqual(KW.input_env(env), {"OT_A": "1"})

    def test_attempt_spec_env_equals_config_env_digest(self):
        d = {"die_gen_env": {"OT_A": "1"}}
        spec_env = {"OT_A": "1", "OT_FLOW_TAG": "flow-20261108", "OT_CELL_WAIVER": "r703"}
        self.assertEqual(KW.gen_env_digest(d, {"gen_env": spec_env}, "x"), KW.gen_env_digest(d, {}, "x"))
        self.assertNotEqual(KW.gen_env_digest(d, {"gen_env": dict(spec_env, OT_A="2")}, "x"), KW.gen_env_digest(d, {}, "x"))

    def test_changed_key_is_named(self):
        self.assertEqual({k for k, v in KW.env_hash_map({"OT_A": "1", "OT_B": "2"}).items() if v != KW.env_hash_map({"OT_A": "1", "OT_B": "3"})[k]}, {"OT_B"})


class StructStop(unittest.TestCase):
    """COORD FLOW-1400 (3): structural verdicts are data keyed by plan block; one force = one launch, nothing standing"""

    def logs_ap(self):
        logs = []
        return type("AP", (), {"log": staticmethod(logs.append)})(), logs

    def st(self):
        return {"struct_stops": {"s81|col_h9_r1__*|bABCDEF123456": {"die": "s81", "item": "col_h9_r1__*", "block": "ABCDEF123456", "verdict": "EXHAUSTED", "owner": "S81-COL-FLOW", "why": "GRT-0116", "force_once": False}}}

    def test_same_block_refused_other_block_and_other_item_pass(self):
        st, cfg = self.st(), {"dies": {"s81": {}}}
        self.assertIn("STRUCT-STOP EXHAUSTED", KW.struct_stop_gate(None, cfg, st, "s81", "col_h9_r1__t1", "ABCDEF123456789"))
        self.assertEqual(KW.struct_stop_gate(None, cfg, st, "s81", "col_h9_r1__t1", "999999999999"), "")
        self.assertEqual(KW.struct_stop_gate(None, cfg, st, "s81", "other__t1", "ABCDEF123456789"), "")
        self.assertEqual(KW.struct_stop_gate(None, cfg, st, "s81", "col_h9_r1__t1", None), "")

    def test_force_is_one_launch_and_stop_stands_again(self):
        ap, logs = self.logs_ap()
        st, cfg = self.st(), {"dies": {"s81": {}}}
        next(iter(st["struct_stops"].values()))["force_once"] = True
        self.assertEqual(KW.struct_stop_gate(None, cfg, st, "s81", "col_h9_r1__t1", "ABCDEF123456"), "")          # select sees the force: not refused
        self.assertEqual(KW.struct_stop_gate(ap, cfg, st, "s81", "col_h9_r1__t1", "ABCDEF123456", consume=True), "")   # the launch spends it
        self.assertTrue(any("STRUCT-FORCE" in m for m in logs))
        self.assertIn("STRUCT-STOP", KW.struct_stop_gate(None, cfg, st, "s81", "col_h9_r1__t1", "ABCDEF123456"))     # and the next launch is refused again


class CancelRowsCore(unittest.TestCase):
    """COORD 11-18: stops first, then exact cancels of the live rows; other items and finished rows untouched"""

    def test_stops_placed_before_cancel_and_only_live_matching_rows(self):
        order = []
        st = {"items": {
            "a": {"die": "s81", "item": "col_h9_r1__t1", "block_sha": "AAAAAAAAAAAAAA", "status": "RUNNING", "attempt": 1},
            "b": {"die": "s81", "item": "col_h9_r1__t2", "block_sha": "BBBBBBBBBBBBBB", "status": "ENQUEUED", "attempt": 2},
            "c": {"die": "s81", "item": "col_h9_r2__t1", "block_sha": "CCCCCCCCCCCCCC", "status": "RUNNING", "attempt": 1},
            "d": {"die": "s81", "item": "col_h9_r1__t3", "block_sha": "DDDDDDDDDDDDDD", "status": "FAIL", "attempt": 1}}}
        orig = KW.grt_arm_cancel
        KW.grt_arm_cancel = lambda AP, cfg, rec, why, cls, jobs, notices, reclaim=True: order.append((rec["item"], cls, reclaim, bool(st["struct_stops"])))
        try:
            stops, done = KW.cancel_rows_core(object(), {}, st, "s81", "col_h9_r1__*", "GRT overflow", "S81-DIE-R3", "GEOMETRY", {})
        finally:
            KW.grt_arm_cancel = orig
        self.assertEqual(stops, 2)
        self.assertEqual(sorted(x[1] for x in done), ["col_h9_r1__t1", "col_h9_r1__t2"])
        self.assertTrue(all(o[1] == "STRUCT-STOP" and o[2] is False and o[3] for o in order))      # stop stored before each cancel, run data kept
        self.assertIsNotNone(KW.struct_stop_for(st, "s81", "col_h9_r1__t1", "AAAAAAAAAAAAAA")[0])
        self.assertIsNone(KW.struct_stop_for(st, "s81", "col_h9_r2__t1", "CCCCCCCCCCCCCC")[0])

    def test_dry_run_changes_nothing(self):
        st = {"items": {"a": {"die": "s81", "item": "col_h9_r1__t1", "block_sha": "A" * 14, "status": "RUNNING", "attempt": 1}}}
        stops, done = KW.cancel_rows_core(object(), {}, st, "s81", "col_h9_r1__*", "x", "o", "GEOMETRY", {}, dry=True)
        self.assertEqual((stops, len(done), st.get("struct_stops")), (0, 1, None))


class OldPlansOnly(unittest.TestCase):
    """COORD 11-18 (D8e applied): rows launched on the applied plan are never cancelled or stopped by --old-plans-only"""

    def test_cancel_rows_skips_rows_on_the_current_plan(self):
        cfg = {"dies": {"s81": {"plan_sha256": "DF7446E48BA9" + "0" * 52}}}
        st = {"items": {
            "old": {"die": "s81", "item": "col_h9_r1__a", "block_sha": "A" * 14, "plan_sha": "e291d6a8e740" + "0" * 52, "status": "RUNNING", "attempt": 1},
            "new": {"die": "s81", "item": "col_h9_r1__b", "block_sha": "B" * 14, "plan_sha": "df7446e48ba9" + "0" * 52, "status": "RUNNING", "attempt": 1}}}
        stops, done = KW.cancel_rows_core(object(), cfg, st, "s81", "col_h9_r1__*", "x", "o", "GEOMETRY", {}, dry=True, old_plans_only=True)
        self.assertEqual([d[1] for d in done], ["col_h9_r1__a"])
        stops, done = KW.cancel_rows_core(object(), cfg, st, "s81", "col_h9_r1__*", "x", "o", "GEOMETRY", {}, dry=True)
        self.assertEqual(len(done), 2)


class ClassifierWritesStop(unittest.TestCase):
    """COORD FLOW-1555: a STRUCTURAL verdict stores its own stop for the plan block; the next block is another key"""

    def test_structural_fail_writes_a_stop_for_its_block_only(self):
        cfg = {"dies": {"s81": {"event": "E"}}}
        st = {}
        rec = {"die": "s81", "item": "col_h9_r1__t1", "block_sha": "AAAAAAAAAAAAAAAA", "attempt": 3, "stage": "place", "dir": ""}
        KW.note_fail_key(cfg, st, rec, "STRUCTURAL", "gpl noconverge @place: overflow")
        self.assertIsNotNone(KW.struct_stop_for(st, "s81", "col_h9_r1__t1", "AAAAAAAAAAAAAAAA")[0])
        self.assertEqual(KW.struct_stop_for(st, "s81", "col_h9_r1__t1", "BBBBBBBBBBBBBBBB"), (None, None))      # a new plan block releases it
        self.assertTrue(next(iter(st["struct_stops"].values()))["auto"])

    def test_other_classes_write_nothing(self):
        st = {}
        KW.note_fail_key({"dies": {"s81": {}}}, st, {"die": "s81", "item": "x", "block_sha": "A" * 16, "attempt": 1, "stage": "gen", "dir": ""}, "FLOW", "ValueError @gen: x")
        self.assertFalse(st.get("struct_stops"))


class SupersedeUnderStopsOff(unittest.TestCase):
    """COORD 11-18 (D8e): ENQUEUED rows on a dead plan block are retired by the tick, opt-out or not, running queue job or not"""

    def run_it(self, qstatus, opt_out=True, so=True):
        cfg = {"stops_off": so, "supersede_max_per_tick": 1000,
               "dies": {"s81": {"event": "E", "enabled": True, "cancel_superseded": False if opt_out else True, "plan": "p", "gen_host": "h"}}}
        st = {"items": {"s81|E|t|bOLD": {"die": "s81", "item": "t", "event": "E", "block_sha": "OLD", "status": "ENQUEUED", "q_id": "j1", "attempt": 16, "dir": "/nonexistent"}},
              "plans": {"h:p|E": {"blocks": {"t": "NEW"}}}}
        jobs_dir = None
        logs = []
        ap = type("AP", (), {"DRY": False, "HUB_NAME": "hub", "log": staticmethod(logs.append), "sh": staticmethod(lambda *a, **k: (0, "", ""))})()
        import tempfile, json as _j
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "state.json").write_text(_j.dumps({"jobs": {"j1": {"status": qstatus, "unit": "u1"}}}))
            orig = KW.stop_on_fleet_bg
            KW.stop_on_fleet_bg = lambda AP, roots: {}
            try:
                KW.cancel_superseded(ap, cfg, st, {}, tmp)
            finally:
                KW.stop_on_fleet_bg = orig
        return st["items"]["s81|E|t|bOLD"]

    def test_done_or_running_queue_job_row_on_a_dead_block_is_retired(self):
        for q in ("RUNNING", "DONE-CRASH", "ORPHAN"):
            r = self.run_it(q)
            self.assertEqual((r["status"], r["class"]), ("CANCELLED", "SUPERSEDED"), q)

    def test_opt_out_still_holds_without_stops_off(self):
        self.assertEqual(self.run_it("RUNNING", opt_out=True, so=False)["status"], "ENQUEUED")


class DeferResign(unittest.TestCase):
    """OWNER r711: superseded-signed types go last and launch only on spare capacity until plan_frozen"""

    def st(self):
        return {"items": {"s81|E|t1|bOLD": {"die": "s81", "item": "t1", "block_sha": "OLDOLDOLDOLD00", "status": "ENQUEUED", "q_status": "SIGNED"}}}

    def test_index_and_predicate(self):
        idx = KW.signed_block_index(self.st(), "s81")
        self.assertTrue(KW.is_superseded_signed(idx, "t1", "NEWNEWNEWNEW00"))
        self.assertFalse(KW.is_superseded_signed(idx, "t1", "OLDOLDOLDOLD00"))        # signed on this very block
        self.assertFalse(KW.is_superseded_signed(idx, "t2", "NEWNEWNEWNEW00"))        # never signed
        self.assertFalse(KW.is_superseded_signed(idx, "t1", None))

    def test_deferred_while_another_pick_exists_and_logged_once(self):
        logs = []
        ap = type("AP", (), {"log": staticmethod(logs.append)})()
        st = {}
        per_die = [[("s81", {"item": "t1", "block_sha": "B1", "_resign": True}), ("s81", {"item": "t2", "block_sha": "B2"})]]
        out = KW.defer_resign(ap, st, per_die, {})
        self.assertEqual([r["item"] for _, r in out[0]], ["t2"])
        KW.defer_resign(ap, st, per_die, {})
        self.assertEqual(sum("DEFER-RESIGN s81 t1" in m for m in logs), 1)

    def test_launches_on_spare_capacity(self):
        per_die = [[("s81", {"item": "t1", "block_sha": "B1", "_resign": True})], [("hbm", {"item": "x", "_resign": True})]]
        self.assertEqual(KW.defer_resign(None, {}, per_die, {}), per_die)

    def test_select_tags_and_orders_last_unless_plan_frozen(self):
        cfg = {"dies": {"s81": {"event": "E", "only_items": None}}, "stops_off": True}
        src = open(KW.__file__).read()
        self.assertIn("is_superseded_signed(_sidx, r[\"item\"], r.get(\"block_sha\"))", src)
        self.assertIn("if not d.get(\"plan_frozen\"):", src)

    def test_unstarted_enqueued_row_is_retired_running_is_kept(self):
        st = self.st()
        st["items"]["s81|E|t1|bNEW"] = {"die": "s81", "item": "t1", "block_sha": "NEWNEWNEWNEW00", "status": "ENQUEUED", "q_status": "QUEUED", "attempt": 1}
        st["items"]["s81|E|t3|bNEW"] = {"die": "s81", "item": "t3", "block_sha": "NEWNEWNEWNEW00", "status": "ENQUEUED", "q_status": "RUNNING", "attempt": 1}
        st["items"]["s81|E|t3|bOLD"] = {"die": "s81", "item": "t3", "block_sha": "OLD", "status": "ENQUEUED", "q_status": "SIGNED"}
        logs = []
        ap = type("AP", (), {"DRY": True, "log": staticmethod(logs.append)})()
        cfg = {"stops_off": True, "dies": {"s81": {"event": "E"}}}
        self.assertEqual(KW.retire_resign_unstarted(ap, cfg, st), 1)
        self.assertEqual(st["items"]["s81|E|t1|bNEW"]["status"], "CANCELLED")
        self.assertEqual(st["items"]["s81|E|t3|bNEW"]["status"], "ENQUEUED")
        cfg["dies"]["s81"]["plan_frozen"] = True
        st["items"]["s81|E|t1|bNEW"].update(status="ENQUEUED")
        self.assertEqual(KW.retire_resign_unstarted(ap, cfg, st), 0)


class UnclassifiedFail(unittest.TestCase):
    """COORD FLOW-1950 N: an unmatched failure is UNCLASSIFIED (not FLOW) and waits for a lane; a check can name its own class"""

    def test_unmatched_failure_is_unclassified(self):
        cls, why = KW.classify("place", "Warning: nothing the rules know about\nKW_PLACE_RC=1\n")
        self.assertEqual(cls, "UNCLASSIFIED")
        self.assertIn("unclassified failure @place", why)

    def test_check_names_its_own_class(self):
        self.assertEqual(KW.classify("gen", "x\nOT_CLASS: design face-bank fit error: 3 faces do not fit\n")[0], "PLAN")
        self.assertEqual(KW.classify("gen", "OT_CLASS: flow staged script missing\n")[0], "FLOW")
        cls, why = KW.classify("gen", "OT_CLASS: design face-bank fit error\n")
        self.assertIn("face-bank fit error", why)

    def test_one_relaunch_only_when_inputs_changed(self):
        cfg = {"dies": {"s81": {"event": "E", "src_manifest_hash": "snap2", "gen_env": {}, "_plan_sha": "p1"}}}
        r = {"item": "x", "block_sha": "blk"}
        old_parts = KW.input_parts({"dies": {"s81": {"event": "E", "src_manifest_hash": "snap1", "gen_env": {}, "_plan_sha": "p1"}}}, "s81", "x", "blk")
        rec = {"class": "UNCLASSIFIED", "status": "FAIL", "attempt": 4, "stage": "place", "reason": "r", "block_sha": "blk", "input_parts": old_parts}
        self.assertFalse(KW.unclassified_hold(cfg, "s81", r, rec, set()))                     # snapshot changed: one relaunch
        rec2 = dict(rec, input_parts=KW.input_parts(cfg, "s81", "x", "blk"))
        self.assertTrue(KW.unclassified_hold(cfg, "s81", r, rec2, set()))                      # nothing changed: stays FAIL
        self.assertTrue(KW.unclassified_hold(cfg, "s81", r, dict(rec, unclass_n=1), set()))     # already relaunched once
        self.assertFalse(KW.unclassified_hold(cfg, "s81", r, rec2, {"x@4"}))                    # a retry key forces
        self.assertFalse(KW.unclassified_hold(cfg, "s81", r, dict(rec2, class_="x", **{"class": "FLOW"}), set()))

    def test_needs_lane_row_posted_once(self):
        cfg = {"dies": {"s81": {"event": "E", "src_manifest_hash": "snap", "gen_env": {}, "_plan_sha": "p1"}}}
        ip = KW.input_parts(cfg, "s81", "x", "blk")
        st = {"items": {"k": {"die": "s81", "item": "x", "event": "E", "status": "FAIL", "class": "UNCLASSIFIED", "attempt": 2, "stage": "place", "reason": "odd", "block_sha": "blk", "input_parts": ip}}}
        posts, logs = [], []
        ap = type("AP", (), {"DRY": False, "coord_append": staticmethod(lambda f, t: posts.append(t)), "log": staticmethod(logs.append)})()
        self.assertEqual(KW.unclassified_needs_lane(ap, cfg, st), 1)
        self.assertEqual(KW.unclassified_needs_lane(ap, cfg, st), 0)
        self.assertIn("NEEDS-LANE [UNCLASSIFIED", posts[0])

    def test_classify_fail_cmd_releases_rows(self):
        import tempfile, json as _j, argparse
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, KW.STATE_FILE).write_text(_j.dumps({"items": {
                "a": {"die": "s81", "item": "t1", "status": "FAIL", "class": "UNCLASSIFIED", "attempt": 3},
                "b": {"die": "s81", "item": "t2", "status": "FAIL", "class": "UNCLASSIFIED", "attempt": 1}}}))
            ns = argparse.Namespace(ap_dir=tmp, die="s81", item="t1", attempt=None, cls="PLAN", owner="S81-X")
            self.assertEqual(KW.classify_fail_cmd(ns), 0)
            st = _j.loads(Path(tmp, KW.STATE_FILE).read_text())
            self.assertEqual((st["items"]["a"]["class"], st["items"]["b"]["class"]), ("PLAN", "UNCLASSIFIED"))


class CliUnderIsolatedPython(unittest.TestCase):
    """COORD 11-18: the kit_wave.py CLI subcommands run under python3 -I (no script dir on sys.path)"""

    def test_classify_fail_runs_with_dash_I(self):
        import subprocess, tempfile, json as _j
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, KW.STATE_FILE).write_text(_j.dumps({"items": {"a": {"die": "s81", "item": "t1", "status": "FAIL", "class": "UNCLASSIFIED", "attempt": 1}}}))
            p = subprocess.run([sys.executable, "-I", KW.__file__, "classify-fail", "--die", "s81", "--item", "t1", "--class", "PLAN", "--ap-dir", tmp],
                               capture_output=True, text=True, timeout=120, cwd="/")
            self.assertEqual(p.returncode, 0, p.stderr[-400:])
            self.assertIn("1 UNCLASSIFIED row(s)", p.stdout)
            self.assertEqual(_j.loads(Path(tmp, KW.STATE_FILE).read_text())["items"]["a"]["class"], "PLAN")


class SnapshotNeutralBlockHash(unittest.TestCase):
    """COORD 11-18 (FABLE-FIX-HEAD-MESH): two snapshots of the same plan give the same per-type normalized hashes"""

    def node(self, root):
        return {"type": {"clock": {"sink_bins_file": f"{root}/physical/die_plan/s81_head/prep/NF6/assets/sink_bins_1.json",
                                   "lef": f"{root}/physical/die_plan/s81_head/prep/views/x.lef"}, "n": 3}, "budget": None}

    def test_same_plan_in_two_snapshots_same_hash(self):
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmp:
            roots = []
            for name in ("snap_s81_head/s81_head_r4_s0", "snap_s81_head/s81_head_r5_s0", "src_s81_pin_abc123_work"):
                r = f"{tmp}/{name}"
                os.makedirs(f"{r}/physical/die_plan/s81_head/prep/NF6/assets")
                os.makedirs(f"{r}/physical/die_plan/s81_head/prep/views")
                open(f"{r}/physical/die_plan/s81_head/prep/NF6/assets/sink_bins_1.json", "w").write("{\"bins\": 1}")
                open(f"{r}/physical/die_plan/s81_head/prep/views/x.lef", "w").write("LEF")
                roots.append(r)
            h = [BI.fingerprint(BI.norm_tree_paths(self.node(r))) for r in roots]
            self.assertEqual(len(set(h)), 1)
            raw = [BI.fingerprint(self.node(r)) for r in roots]
            self.assertEqual(len(set(raw)), 3)                                  # the raw hash moves with the snapshot name

    def test_changed_content_changes_the_hash(self):
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmp:
            hs = []
            for name, body in (("snap_x/x_r1_s0", "a"), ("snap_x/x_r2_s0", "b")):
                r = f"{tmp}/{name}"
                os.makedirs(f"{r}/physical/die_plan/s81_head/prep/NF6/assets")
                os.makedirs(f"{r}/physical/die_plan/s81_head/prep/views")
                open(f"{r}/physical/die_plan/s81_head/prep/NF6/assets/sink_bins_1.json", "w").write(body)
                open(f"{r}/physical/die_plan/s81_head/prep/views/x.lef", "w").write("LEF")
                hs.append(BI.fingerprint(BI.norm_tree_paths(self.node(r))))
            self.assertNotEqual(hs[0], hs[1])

    def test_probe_uses_the_shared_normalizer(self):
        self.assertIn("norm_tree_paths(prof[", KW.PROBE_PLAN)
        self.assertEqual(KW.PROBE_V, 10)


class DieContextHash(unittest.TestCase):
    """COORD 11-18 (QC N4.2): a die-level change a type consumes changes its die_ctx; an unrelated die key does not"""

    def plan(self, **clock):
        c = {"insertion_ps": 100, "seam_hold": {"sender_ps": 25, "seam_ps": 110, "per_type_ps": {"slw_hc1": 160}}, "tap_window": {"window_ps": 20}}
        c.update(clock)
        return {"partition_types": {"slw_stm": {"x": 1}, "slw_hc1": {"x": 1}, "slw_hc1__a1_0001": {"x": 1}}, "clock": c, "reset": {"n": 1}, "die": {"w": 5},
                "census": [1], "ports": [1, 2], "note": "free text"}

    def test_die_seam_change_hits_types_on_the_die_value_not_per_type_overridden(self):
        a, b = self.plan(), self.plan(seam_hold={"sender_ps": 25, "seam_ps": 100, "per_type_ps": {"slw_hc1": 160}})
        self.assertNotEqual(BI.die_ctx(a, "slw_stm"), BI.die_ctx(b, "slw_stm"))
        self.assertEqual(BI.die_ctx(a, "slw_hc1"), BI.die_ctx(b, "slw_hc1"))              # its per_type_ps 160 did not move
        self.assertEqual(BI.die_ctx(a, "slw_hc1__a1_0001"), BI.die_ctx(b, "slw_hc1__a1_0001"))   # variant-stripped name resolves too

    def test_per_type_override_change_hits_only_that_type(self):
        a, b = self.plan(), self.plan(seam_hold={"sender_ps": 25, "seam_ps": 110, "per_type_ps": {"slw_hc1": 110}})
        self.assertNotEqual(BI.die_ctx(a, "slw_hc1"), BI.die_ctx(b, "slw_hc1"))
        self.assertNotEqual(BI.die_ctx(a, "slw_hc1__a1_0001"), BI.die_ctx(b, "slw_hc1__a1_0001"))
        self.assertEqual(BI.die_ctx(a, "slw_stm"), BI.die_ctx(b, "slw_stm"))

    def test_other_clock_keys_change_every_type_unrelated_keys_none(self):
        a = self.plan()
        self.assertNotEqual(BI.die_ctx(a, "slw_stm"), BI.die_ctx(self.plan(tap_window={"window_ps": 30}), "slw_stm"))
        b = self.plan(); b["census"] = [9]; b["ports"] = [3]; b["note"] = "other"; b["clock"]["seam_hold"]["note"] = "text"; b["partition_types"]["other"] = {"y": 2}
        self.assertEqual(BI.die_ctx(a, "slw_stm"), BI.die_ctx(b, "slw_stm"))

    def test_row_kept_only_when_die_ctx_matches(self):
        cur = {"qwen_compute": {"t": "NEW"}}
        self.assertTrue(KW.ctx_changed(cur, "qwen_compute", {"item": "t", "die_ctx": "OLD"}))
        self.assertFalse(KW.ctx_changed(cur, "qwen_compute", {"item": "t", "die_ctx": "NEW"}))
        self.assertFalse(KW.ctx_changed(cur, "qwen_compute", {"item": "t"}))               # unknown stays as before
        self.assertFalse(KW.ctx_changed({}, "qwen_compute", {"item": "t", "die_ctx": "OLD"}))

    def test_probe_emits_die_ctx(self):
        self.assertIn("die_ctx(p, name)", KW.PROBE_PLAN)
        self.assertEqual(KW.PROBE_V, 10)


class DieContextTypeScoped(unittest.TestCase):
    """COORD 11-18: die_ctx is type-scoped: a per-type clock / reset / latency row change for A moves A only"""

    def plan(self):
        names = ["A", "B"] + ["T%d" % i for i in range(14)]
        return {"partition_types": {n: {"x": 1} for n in names},
                "clock": {"insertion_ps": 100, "tap_pitch_um": 40, "seam_hold": {"sender_ps": 25, "seam_ps": 110},
                          "tap_window": {"window_ps": 20, "per_type_ps": {"A": 30, "B": 40}},
                          "spine": {"layers": ["M6", "M7"], "feed": {"A": {"um": 5}, "B": {"um": 6}}},
                          "landing_network": {"edges": [{"from": "A", "to": "T0", "ps": 10}, {"from": "T1", "to": "T2", "ps": 12}]},
                          "pad_clock": {"pins": [{"type": "A", "pin": "p0"}, {"type": "B", "pin": "p1"}]}},
                "reset": {"sync_stages": 2, "in_sites": {n: [1, 2] for n in ["A", "B"] + ["T%d" % i for i in range(14)]}},
                "die": {"period_ps": 400, "channels": [{"reason": "x", "rect_um": [1, 2]}]},
                "latency": {"lanes": {"lane%d" % i: {"d": i, "recv": ("A" if i == 0 else "T%d" % (i % 14))} for i in range(20)}}}

    def mod(self, f):
        p = self.plan()
        f(p)
        return p

    def test_per_type_clock_row_change_for_a_moves_a_only(self):
        base = self.plan()
        for f in (lambda p: p["clock"]["tap_window"]["per_type_ps"].update(A=35),
                  lambda p: p["clock"]["pad_clock"]["pins"][0].update(pin="p9"),
                  lambda p: p["clock"]["spine"]["feed"]["A"].update(um=9),
                  lambda p: p["clock"]["landing_network"]["edges"][0].update(ps=11),
                  lambda p: p["reset"]["in_sites"].update(A=[1, 2, 3]),
                  lambda p: p["latency"]["lanes"]["lane0"].update(d=99)):
            q = self.mod(f)
            self.assertNotEqual(BI.die_ctx(base, "A"), BI.die_ctx(q, "A"))
            self.assertEqual(BI.die_ctx(base, "B"), BI.die_ctx(q, "B"))
            self.assertEqual(BI.die_ctx(base, "T3"), BI.die_ctx(q, "T3"))

    def test_die_wide_scalar_moves_every_type_other_types_rows_move_none(self):
        base = self.plan()
        q = self.mod(lambda p: p["clock"].update(tap_pitch_um=50))
        for n in ("A", "B", "T3"):
            self.assertNotEqual(BI.die_ctx(base, n), BI.die_ctx(q, n))
        q = self.mod(lambda p: (p["clock"]["landing_network"]["edges"][1].update(ps=99), p["die"]["channels"].append({"reason": "y"})))
        for n in ("A", "B"):
            self.assertEqual(BI.die_ctx(base, n), BI.die_ctx(q, n))
        q = self.mod(lambda p: p["clock"]["seam_hold"].update(seam_ps=100))
        self.assertNotEqual(BI.die_ctx(base, "A"), BI.die_ctx(q, "A"))


class CtxOnlySupersedeGuard(unittest.TestCase):
    """COORD 11-18: a die_ctx-only change retires ENQUEUED-not-started and gen/place rows; rows past place finish"""

    def run_it(self, status, qstatus, ctx_old="OLD", block_same=True):
        cfg = {"stops_off": True, "supersede_max_per_tick": 1000,
               "dies": {"qwen_compute": {"event": "E", "enabled": True, "plan": "p", "gen_host": "h"}}}
        blk = "BLK"
        st = {"items": {"qwen_compute|E|t|bBLK": {"die": "qwen_compute", "item": "t", "event": "E", "block_sha": blk if block_same else "OLDBLK", "status": status, "q_status": qstatus,
                                                  "q_id": "j1", "attempt": 1, "dir": "/nonexistent", "die_ctx": ctx_old}},
              "plans": {"h:p|E": {"blocks": {"t": blk}, "norm_blocks": {"t": "N"}, "die_ctx": {"t": "NEW"}}}}
        import tempfile, json as _j
        logs = []
        ap = type("AP", (), {"DRY": False, "HUB_NAME": "hub", "log": staticmethod(logs.append), "sh": staticmethod(lambda *a, **k: (0, "", ""))})()
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "state.json").write_text(_j.dumps({"jobs": {"j1": {"status": qstatus, "unit": "u1"}}}))
            orig = KW.stop_on_fleet_bg
            KW.stop_on_fleet_bg = lambda AP, roots: {}
            try:
                KW.cancel_superseded(ap, cfg, st, {}, tmp)
            finally:
                KW.stop_on_fleet_bg = orig
        return st["items"]["qwen_compute|E|t|bBLK"]["status"]

    def test_row_past_place_finishes(self):
        self.assertEqual(self.run_it("ENQUEUED", "RUNNING"), "ENQUEUED")

    def test_unstarted_enqueued_and_wave_gen_place_rows_are_retired(self):
        self.assertEqual(self.run_it("ENQUEUED", "QUEUED"), "CANCELLED")
        self.assertEqual(self.run_it("RUNNING", None), "CANCELLED")

    def test_same_die_ctx_is_untouched_and_block_change_still_retires(self):
        self.assertEqual(self.run_it("ENQUEUED", "RUNNING", ctx_old="NEW"), "ENQUEUED")


class FixesItems(unittest.TestCase):
    """COORD 11-18: a commit trailer  Fixes-Items: die/item  relaunches the FAILED rows of those items on the first tick whose rt tree carries the commit"""
    LOG = ("aaaaaaaaaaaa1111\x1fSubject\n\nbody\nFixes-Items: s81/ot_s81sl_leaf__t56, eng__t1\nFixes-Items: qwen_*/gunit__t1\n\x1e"
           "bbbbbbbbbbbb2222\x1fother commit, no trailer\x1e")

    def ap(self, log=None, rc=0):
        logs, calls = [], []
        def sh(cmd, timeout=0, **k):
            calls.append(cmd)
            return rc, (log if log is not None else self.LOG), ""
        return type("AP", (), {"REPO": "/repo", "log": staticmethod(logs.append), "sh": staticmethod(sh)})(), logs, calls

    def state(self):
        return {"items": {
            "a": {"die": "s81", "item": "ot_s81sl_leaf__t56", "event": "E", "attempt": 3, "status": "FAIL", "class": "UNCLASSIFIED", "started": 5},
            "b": {"die": "s81", "item": "eng__t1", "event": "E", "attempt": 1, "status": "FAIL", "class": "FLOW", "started": 5},
            "c": {"die": "qwen_compute", "item": "gunit__t1", "event": "E", "attempt": 2, "status": "FAIL", "class": "PLAN", "started": 5},
            "d": {"die": "s81", "item": "other", "event": "E", "attempt": 1, "status": "FAIL", "started": 5},
            "e": {"die": "s81", "item": "eng__t1", "event": "OLD", "attempt": 9, "status": "FAIL", "started": 9}}}

    def cfg(self):
        return {"dies": {"s81": {"event": "E"}, "qwen_compute": {"event": "E"}, "hbm": {"event": "E"}}}

    def test_trailer_parsing(self):
        got = KW.parse_fixes_log(self.LOG)
        self.assertEqual(got, [("aaaaaaaaaaaa", "s81", "ot_s81sl_leaf__t56"), ("aaaaaaaaaaaa", "*", "eng__t1"), ("aaaaaaaaaaaa", "qwen_*", "gunit__t1")])

    def test_first_tick_after_rt_carries_the_commit_forces_the_failed_rows(self):
        ap, logs, calls = self.ap()
        st, cfg, notices = self.state(), self.cfg(), {}
        self.assertEqual(KW.fixes_release(ap, cfg, st, notices, rt_sha="0" * 12), 0)           # first sight: history is not replayed
        self.assertEqual(st["fixes_seen"], "0" * 12)
        n = KW.fixes_release(ap, cfg, st, notices, rt_sha="1" * 12)
        self.assertEqual(n, 3)
        self.assertIn("0" * 12 + ".." + "1" * 12, calls[0])
        self.assertEqual(sorted(cfg["dies"]["s81"]["retry"]), ["eng__t1@1", "ot_s81sl_leaf__t56@3"])      # current event only: the OLD-event eng__t1@9 is not touched
        self.assertEqual(cfg["dies"]["qwen_compute"]["retry"], ["gunit__t1@2"])
        self.assertNotIn("retry", cfg["dies"]["hbm"])
        self.assertTrue(any("FIX-RELAUNCH s81/eng__t1@1" in m for m in logs))

    def test_stays_forced_until_the_row_relaunches_then_clears(self):
        ap, logs, calls = self.ap()
        st, cfg = self.state(), self.cfg()
        KW.fixes_release(ap, cfg, st, {}, rt_sha="0" * 12)
        KW.fixes_release(ap, cfg, st, {}, rt_sha="1" * 12)
        cfg2 = self.cfg()
        KW.fixes_release(ap, cfg2, st, {}, rt_sha="1" * 12)                                      # next tick, still FAIL: forced again (in memory only)
        self.assertIn("eng__t1@1", cfg2["dies"]["s81"]["retry"])
        st["items"]["b"]["status"] = "RUNNING"
        cfg3 = self.cfg()
        KW.fixes_release(ap, cfg3, st, {}, rt_sha="1" * 12)
        self.assertNotIn("eng__t1@1", cfg3["dies"]["s81"].get("retry", []))
        self.assertNotIn("s81|eng__t1@1", st["fixes_pending"])
        self.assertEqual(sum("FIX-RELAUNCH s81/eng__t1@1" in m for m in logs), 1)               # logged once

    def test_unreadable_commit_range_waits_and_does_not_mark_seen(self):
        ap, logs, calls = self.ap(rc=128)
        st, cfg = self.state(), self.cfg()
        KW.fixes_release(ap, cfg, st, {}, rt_sha="0" * 12)
        self.assertEqual(KW.fixes_release(ap, cfg, st, {}, rt_sha="1" * 12), 0)
        self.assertEqual(st["fixes_seen"], "0" * 12)


class FlowFixes2355(unittest.TestCase):
    """FABLE-FLOW-2355: kill-pin onto a changed tree, overlay-only drift at a flow stage, classifier on info lines, HUNG-WATCH small dips"""

    def prev(self, tmp, src="/t/old", mh="HASH1"):
        import json as _j
        Path(tmp, "spec.json").write_text(_j.dumps({"src": src, "plan": "p.json", "src_manifest_hash": mh, "gen_env": {}}))
        return {"dir": tmp, "attempt": 3}

    def test_kill_pin_relaunches_on_the_live_tree_when_the_pinned_tree_changed(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            prev = self.prev(tmp)
            sp = {}
            why = KW.kill_pin(prev, sp, manifest_of=lambda t: "OTHER", live_src="/t/live")
            self.assertIn("relaunching on the live tree", why)
            self.assertNotIn("kill_pin", sp)
            sp = {}
            self.assertEqual(KW.kill_pin(prev, sp, manifest_of=lambda t: "HASH1", live_src="/t/live"), "")      # same content: pinned
            self.assertEqual(sp["src"], "/t/old")
            sp = {}
            self.assertEqual(KW.kill_pin(self.prev(tmp, src="/t/live"), sp, manifest_of=lambda t: "x", live_src="/t/live"), "")   # the live tree itself: no check
            prev = self.prev(tmp)
            self.assertIn("unreadable", KW.kill_pin(prev, {}, manifest_of=lambda t: "", live_src="/t/live"))

    def test_overlay_only_drift_does_not_defeat_skip_at_a_flow_stage(self):
        cfg = {"dies": {"s81": {"event": "E", "src_manifest_hash": "snap", "gen_env": {}, "_plan_sha": "p", "_src_overlay": "OV1"}}}
        ip = KW.input_parts(cfg, "s81", "x", "blk")
        rec = {"status": "FAIL", "stage": "place", "reason": "r", "block_sha": "blk", "input_parts": ip}
        cfg["dies"]["s81"]["_src_overlay"] = "OV2"
        self.assertTrue(KW.so_same_input(cfg, "s81", {"item": "x", "block_sha": "blk"}, rec))
        rec["stage"] = "kit_rtl"                                                         # a bind-stage failure reads the overlay: still a release
        self.assertFalse(KW.so_same_input(cfg, "s81", {"item": "x", "block_sha": "blk"}, rec))
        rec["stage"] = "place"
        cfg["dies"]["s81"]["src_manifest_hash"] = "snap2"
        self.assertFalse(KW.so_same_input(cfg, "s81", {"item": "x", "block_sha": "blk"}, rec))

    def test_info_line_with_outline_is_not_a_plan_geometry_error(self):
        self.assertNotEqual(KW.classify("place", "GRTM mode edge_outline image /x/y.png written\nKW_PLACE_RC=1\n")[1].split(" @")[0], "plan geometry / site")
        self.assertEqual(KW.classify("place", "Error: placement failed: macro outside the die outline\n")[0], "PLAN")

    def test_hung_watch_small_cpu_dip_keeps_the_clock(self):
        t0 = 100000.0
        hung, w, _ = KW.hung_judge({"cpu": 500.0, "t": t0}, {"cpu": 480.0, "log": t0 - 9999}, t0 - 9999, t0 + 130 * 60, 120)
        self.assertTrue(hung)                     # CPU dipped by 20 s (an exited child): the 120-min clock was not reset
        hung, w, _ = KW.hung_judge({"cpu": 5000.0, "t": t0}, {"cpu": 100.0, "log": t0 - 9999}, t0 - 9999, t0 + 130 * 60, 120)
        self.assertFalse(hung)                    # a real restart (CPU fell by thousands of seconds) restarts the clock


class RetryHost(unittest.TestCase):
    """COORD / FLEET-OPS-R 11-18: an INFRA / OOM retry goes to the gen host with the most free memory, not the host that killed it"""

    def cfg(self):
        return {"_hub": "hub", "_otrun_status": {"epyc7": {"admit": 5, "wait_gb": 0}, "epyc8": {"admit": 200, "wait_gb": 50}, "epyc9": {"admit": 120, "wait_gb": 0}, "localhost": {"admit": 300, "wait_gb": 0}},
                "dies": {"s81": {"event": "E", "gen_host": "epyc7", "gen_hosts": ["epyc7", "epyc8", "epyc9"]}}}

    def test_killed_hosts_reads_the_latest_infra_attempt(self):
        st = {"items": {"a": {"die": "s81", "item": "t", "attempt": 22, "status": "FAIL", "class": "FLOW", "started": 1},
                        "b": {"die": "s81", "item": "t", "attempt": 23, "status": "RETRY-INFRA", "class": "INFRA", "started": 2, "gen_host": "epyc7", "ran_on": "epyc7"}}}
        self.assertEqual(KW.killed_hosts(st, "s81", "t"), ["epyc7"])
        st["items"]["b"]["class"] = "FLOW"
        st["items"]["b"]["status"] = "FAIL"
        st["items"]["b"]["reason"] = "design error"
        self.assertEqual(KW.killed_hosts(st, "s81", "t"), [])

    def test_most_free_memory_wins_never_the_hub_the_killer_is_avoided(self):
        cfg = self.cfg()
        self.assertEqual(KW.retry_gen_host(cfg, "s81", "t", ["epyc7"], "epyc7"), "epyc8")           # the hub has 300 free but is never a candidate; epyc8 has 200-50 = 150, epyc9 120
        cfg["dies"]["s81"]["gen_hosts"] = ["hub", "localhost", "epyc7"]
        self.assertEqual(KW.retry_gen_host(cfg, "s81", "t", [], "epyc7"), "epyc7")                  # a hub listed in gen_hosts is dropped too

    def test_without_status_or_alternatives_the_default_stays(self):
        cfg = self.cfg(); cfg["_otrun_status"] = {}
        self.assertEqual(KW.retry_gen_host(cfg, "s81", "t", ["epyc7"], "epyc7"), "epyc7")
