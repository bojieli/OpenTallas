"""WAVE-PILOT-FIX 11-18 (OWNER order via COORD: remove all safety stops): with cfg stops_off no hold record, class breaker, dedupe hold, pilot gate, retry probe or
tree-switch marker blocks a launch.  Infra rails (ot-run admission, disk floor, delete guard, OOM) are not touched."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import flow_guard as FG  # noqa: E402
import hold_records as HR  # noqa: E402
import kit_wave as KW  # noqa: E402

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
