"""WAVE-RECIPE-1 11-14: (d) NEEDS-LANE (no relaunch of an unchanged kit after a design FAIL) and FIX 2 (a killed attempt
resumes its own checkpoint: kill detection on queue rows + kill_pin)."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import kit_wave as K

SPEC = {"item": "slice_station__t8", "event": "B3x2b", "plan": "/p/plan.json", "src": "/s/src_a", "src_sha": "aaa",
        "src_overlay": "ov1", "kit_rtl": {"mode": "bind", "bind_out": "/b/out"}, "gen_args": ["--x"],
        "gen_env": {"OT_GRT_ALLOW_CONGESTION": "1"}}


class _Base(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        self.ad = self.root / "a3"
        self.ad.mkdir()
        (self.ad / "spec.json").write_text(json.dumps(SPEC))
        self.rec = {"die": "s81", "item": "slice_station__t8", "event": "B3x2b", "attempt": 3, "status": "ENQUEUED",
                    "q_status": "FAIL", "q_class": "ROUTING", "q_stage": "route", "dir": str(self.ad),
                    "q_reason": "grt-overflow: drc 0 GRT-0116 overflow 76"}
        self.st = {"items": {"s81|slice_station__t8|b1": self.rec}}
        self.cfg = {"dies": {"s81": {"retry": ["slice_station__t8@3"], "owner_lane": "DIE-S81-92"}}}

    def tearDown(self):
        self.td.cleanup()

    def nl(self, cand=SPEC):
        with mock.patch.object(K, "spec_for", lambda *a, **k: json.loads(json.dumps(cand))), \
                mock.patch.object(K, "leafslew_launch", lambda *a, **k: (None, None)):
            return K.needs_lane(self.cfg, self.st, "s81", "slice_station__t8", self.rec)


class NeedsLaneTest(_Base):
    def test_design_fail_same_inputs_holds_and_is_noted(self):
        self.assertTrue(self.nl())
        e = self.st["needs_lane"]["s81|slice_station__t8"]
        self.assertEqual((e["attempt"], e["cls"], e["stage"], e["posted"]), (3, "ROUTING", "route", 0))

    def test_any_kit_input_change_releases(self):
        for k, v in (("src_sha", "bbb"), ("src_overlay", "ov2"), ("plan", "/p/plan2.json"),
                     ("gen_env", {"OT_GRT_ALLOW_CONGESTION": "1", "OT_GEN_M9_GRANT": "1"}),
                     ("kit_rtl", {"mode": "bind", "bind_out": "/b/out2"})):
            if k == "plan":
                continue                              # plan path is not an input (INPUT_SKIP); the plan sha / block is
            self.assertFalse(self.nl(dict(SPEC, **{k: v})), k)

    def test_infra_and_non_design_flow_are_never_held(self):
        for cls, why in (("INFRA", "infra-stopped: earlyoom"), ("FLOW", "flow-error: TypeError in kit_wave"),
                         ("PLAN", "cell-cap: 632k"), ("RTL", "LEC NOT EQUIVALENT")):
            self.rec.update(q_class=cls, q_reason=why)
            self.assertFalse(self.nl(), cls)

    def test_deterministic_drt_flow_end_is_design(self):
        self.rec.update(q_class="FLOW", q_reason="flow-error: [ERROR DRT-0255] Maze Route cannot find path")
        self.assertTrue(self.nl())

    def test_timing_and_wave_stage_fail(self):
        self.rec.update(q_class="TIMING", q_reason="post-cts-hold: -441 ps")
        self.assertTrue(self.nl())
        self.rec.update(status="FAIL", q_status=None, **{"class": "ROUTING"}, reason="geom GRT overflow", stage="geom")
        self.assertTrue(self.nl())

    def test_same_inputs_retry_fix_and_die_opt_out_release(self):
        self.cfg["dies"]["s81"]["retry_fix"] = {"slice_station__t8@3": "SAME-INPUTS: nondeterministic DRT check"}
        self.assertFalse(self.nl())
        self.cfg["dies"]["s81"]["retry_fix"] = {}
        self.cfg["dies"]["s81"]["needs_lane_gate"] = False
        self.assertFalse(self.nl())

    def test_unmeasured_source_hash_never_holds(self):
        self.assertFalse(self.nl(dict(SPEC, src_overlay="")))
        (self.ad / "spec.json").write_text("{bad json")
        self.assertFalse(self.nl())

    def test_grt_edge_form_added_at_launch_counts_as_change(self):
        self.rec["grt_overflow"] = True
        self.assertFalse(self.nl())                   # launch() adds OT_GRT_TRANSITION_MODE=edge_outline: a new form

    def test_post_once_per_die_and_tsv(self):
        self.assertTrue(self.nl())
        AP = mock.Mock(DRY=False)
        self.assertEqual(K.needs_lane_post(AP, self.cfg, self.st, self.root), 1)
        args = AP.coord_append.call_args[0]
        self.assertEqual(args[0], "lanes/COORD-REVIEW-QUEUE.md")
        self.assertIn("NEEDS-LANE s81", args[1])
        self.assertIn("slice_station__t8@3 ROUTING", args[1])
        self.assertIn("DIE-S81-92", args[1])
        self.assertIn("slice_station__t8\t3", (self.root / K.NEEDS_LANE_FILE).read_text())
        AP.coord_append.reset_mock()
        self.assertTrue(self.nl())                    # still held next tick: no second post
        self.assertEqual(K.needs_lane_post(AP, self.cfg, self.st, self.root), 0)
        AP.coord_append.assert_not_called()


class KillResumeTest(_Base):
    def test_queue_kill_is_detected(self):
        self.rec.update(q_class="INFRA", q_reason="infra-stopped: SIGTERM")
        self.assertTrue(K.killed_attempt(self.rec))
        self.rec.update(q_class="FLOW", q_reason="flow-error: OT_LEGACY_GATE grt FAIL setup PASS exit -15")
        self.assertTrue(K.killed_attempt(self.rec))
        self.rec.update(q_class="ROUTING", q_reason="grt-overflow: 76")
        self.assertFalse(K.killed_attempt(self.rec))
        self.assertFalse(K.killed_attempt({"status": "FAIL", "class": "TIMING", "reason": "post-cts-hold -400"}))
        self.assertTrue(K.killed_attempt({"status": "FAIL", "class": "INFRA", "reason": "make: *** Error 241"}))

    def test_resume_source_allows_nochange_for_a_queue_kill(self):
        self.rec.update(q_class="INFRA", q_reason="infra-stopped: SIGTERM", kit="intel1:/k/K")
        AP = mock.Mock(AP_DIR=str(self.root))
        self.assertTrue(K.resume_source(AP, self.rec)["allow_nochange"])
        self.rec.update(q_class="ROUTING", q_reason="grt-overflow: 76")
        self.assertFalse(K.resume_source(AP, self.rec)["allow_nochange"])

    def test_kill_pin_copies_the_killed_attempt_inputs(self):
        sp = dict(SPEC, src="/s/src_new", src_sha="new", src_overlay="ov9", plan="/p/new.json",
                  gen_env={"OT_GEN_M9_GRANT": "1"}, gen_host="epyc9", work="/w/attempt_4")
        self.assertEqual(K.kill_pin(self.rec, sp), "")
        for k in ("src", "src_sha", "src_overlay", "plan", "kit_rtl", "gen_args", "gen_env"):
            self.assertEqual(sp[k], SPEC[k], k)
        self.assertEqual((sp["gen_host"], sp["work"]), ("epyc9", "/w/attempt_4"))     # placement stays the new attempt's
        self.assertEqual(sp["kill_pin"]["attempt"], 3)

    def test_kill_pin_fails_closed(self):
        (self.ad / "spec.json").write_text(json.dumps({"plan": "/p"}))
        sp = dict(SPEC)
        self.assertIn("lacks src", K.kill_pin(self.rec, sp))
        self.assertEqual(sp, SPEC)


class FlowRegenTest(unittest.TestCase):
    """FIX 5: an unstarted stale kit regenerates on the current die flow; a started one is never touched"""
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        self.d = {"enabled": True, "event": "B3x2b", "src_sha": "aaa",
                  "die_gen_env": {"OT_HOLD_STOP_PS": "-1000000", "OT_GRT_ALLOW_CONGESTION": "1"},
                  "item_env": {"t_own": {"OT_GRT_ALLOW_CONGESTION": "0"}}}
        self.cfg = {"dies": {"s81": self.d}}
        self.st = {"items": {}}

    def tearDown(self):
        self.td.cleanup()

    def row(self, item, gen_env, src_sha="aaa", **kw):
        ad = self.root / item
        ad.mkdir()
        (ad / "spec.json").write_text(json.dumps({"src_sha": src_sha, "gen_env": gen_env}))
        r = dict({"die": "s81", "item": item, "event": "B3x2b", "attempt": 2, "status": "RUNNING", "unit": f"kw-{item}",
                  "dir": str(ad)}, **kw)
        self.st["items"][f"s81|{item}"] = r
        return r

    def run_regen(self, started=False, progress=""):
        AP = mock.Mock(DRY=False)
        with mock.patch.object(K, "volume_started", lambda r: started), \
                mock.patch.object(K, "heavy_progress", lambda r: progress), \
                mock.patch.object(K, "stop_reason", lambda *a: ""), \
                mock.patch.object(K, "counted_now", lambda *a, **k: False):
            return K.flow_regen(AP, self.cfg, self.st, {}), AP

    def test_stale_unstarted_kit_regenerates(self):
        r = self.row("t_old", {"OT_GRT_ALLOW_CONGESTION": "1"})               # no hold-stop removal: stale
        n, AP = self.run_regen()
        self.assertEqual(n, 1)
        self.assertEqual(r["status"], "RETRY-INFRA")
        self.assertIn("OT_HOLD_STOP_PS", r["reason"])
        AP.sh.assert_any_call(["systemctl", "--user", "stop", "kw-t_old"], timeout=180)

    def test_current_and_item_owned_kits_stay(self):
        self.row("t_cur", {"OT_HOLD_STOP_PS": "-1000000", "OT_GRT_ALLOW_CONGESTION": "1"})
        self.row("t_own", {"OT_HOLD_STOP_PS": "-1000000", "OT_GRT_ALLOW_CONGESTION": "0"})   # item_env wins: not stale
        self.assertEqual(self.run_regen()[0], 0)

    def test_started_or_progressed_kit_is_never_touched(self):
        r = self.row("t_old", {})
        self.assertEqual(self.run_regen(started=True)[0], 0)
        self.assertEqual(self.run_regen(progress="place")[0], 0)
        self.assertEqual(r["status"], "RUNNING")

    def test_src_bump_is_stale_but_a_kill_pin_is_not(self):
        cur = {"OT_HOLD_STOP_PS": "-1000000", "OT_GRT_ALLOW_CONGESTION": "1"}
        self.row("t_src", cur, src_sha="old")
        self.assertEqual(self.run_regen()[0], 1)
        ad = self.root / "t_pin"
        ad.mkdir()
        (ad / "spec.json").write_text(json.dumps({"src_sha": "old", "gen_env": cur, "kill_pin": {"attempt": 1}}))
        self.st["items"]["s81|t_pin"] = {"die": "s81", "item": "t_pin", "event": "B3x2b", "attempt": 2, "status": "RUNNING",
                                         "unit": "kw-t_pin", "dir": str(ad)}
        self.assertEqual(self.run_regen()[0], 0)

    def test_held_rows_and_opt_out(self):
        self.row("t_old", {})
        self.d["hold_items"] = {"t_*": "plan event"}
        self.assertEqual(self.run_regen()[0], 0)
        self.d["hold_items"] = {}
        self.d["flow_regen"] = False
        self.assertEqual(self.run_regen()[0], 0)

    def test_failed_row_rearms_on_a_die_env_change(self):
        r = self.row("t_fail", {"OT_GRT_ALLOW_CONGESTION": "1"}, status="ENQUEUED", q_status="FAIL", q_class="TIMING")
        self.assertIn("die_gen_env", K.rearm_changes({}, self.cfg, "s81", self.d, r))
        self.assertEqual(K.die_env_stale(self.d, "t_fail", {"gen_env": dict(self.d["die_gen_env"])}), [])


if __name__ == "__main__":
    unittest.main()
