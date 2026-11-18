"""WAVE-PILOT-FIX 11-17 (OWNER 06:1x): one failing pilot never holds a family; holds name an owner and expire; 3 pilots in parallel."""
import sys, time, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hold_records as HR  # noqa: E402
import kit_wave as KW  # noqa: E402

PLAN = "p" * 64
NOW = 1_800_000_000.0


def cfg(act=None, items=None):
    c = {"_now": NOW, "_registry_lanes": {"OLD-LANE", "LIVE"}, "_lane_activity": act if act is not None else {"LIVE": NOW - 3600, "OTHER": NOW - 60},
         "dies": {"s81": {"event": "EVT1", "plan": "/x/EVT1.json", "plan_sha256": PLAN, "planned_events": ["EVT2"],
                          "hold_event_items": {PLAN: items or ["a__t1", "a__t2", "a__t3", "a__t4", "a__t5", "b__t1"]}}}}
    return c


def rec(**k):
    r = {"id": "r1", "plan_sha": PLAN, "reason": "why", "release": ["event_adopt:EVT2"], "patterns": ["a__*"], "owner": "LIVE", "cause": "shared rck tree"}
    r.update(k)
    return r


class FailScope(unittest.TestCase):
    def row(self, **k):
        r = {"die": "s81", "item": "col_h9_r2__t1", "status": "FAIL"}
        r.update(k)
        return r

    def test_infra_and_flow_never_hold(self):
        for cls in ("INFRA", "INFRA-SSH", "FLOW"):
            self.assertEqual(KW.pilot_fail_scope(self.row(**{"class": cls, "reason": "x"})), "infra")
        q = self.row(status="ENQUEUED", q_status="FAIL", q_class="ROUTING", q_reason="flow-error: [ERROR DRT-0073] No access point for u/clk")
        self.assertEqual(KW.pilot_fail_scope(q), "infra")
        self.assertEqual(KW.pilot_fail_scope(self.row(**{"class": "TIMING", "reason": "stopped from outside exit 143"})), "infra")

    def test_per_instance_design_classes_do_not_hold(self):
        for txt in ("internal hold violations 3 (WNS)", "route DRC 2 M5 shorts", "post-CTS setup -61.4 ps"):
            self.assertEqual(KW.pilot_fail_scope(self.row(**{"class": "ROUTING", "reason": txt})), "instance", txt)
        self.assertEqual(KW.pilot_fail_scope(self.row(status="ENQUEUED", q_status="FAIL", q_class="TIMING",
                                                      q_reason="internal hold violations 12; 2 M5 shorts")), "instance")

    def test_shared_design_class_still_holds(self):
        for txt in ("DRC 1200 violations", "setup -310 ps", "GRT overflow 4000 clk tree"):
            self.assertEqual(KW.pilot_fail_scope(self.row(**{"class": "ROUTING", "reason": txt})), "shared", txt)

    def test_pilot_fail_times_counts_only_shared(self):
        d = {}
        rows = {"1": self.row(**{"class": "FLOW", "updated": 50, "item": "col_h9_r2__t1", "stage": "gen"}),
                "2": self.row(**{"class": "ROUTING", "reason": "DRC 2 shorts", "updated": 60, "item": "col_h9_r2__t2", "stage": "route"})}
        self.assertEqual(KW.pilot_fail_times(d, "s81", {"items": rows}), {})
        rows["3"] = self.row(**{"class": "ROUTING", "reason": "DRC 900 violations", "updated": 70, "item": "col_h9_r2__t3", "stage": "route"})
        self.assertEqual(list(KW.pilot_fail_times(d, "s81", {"items": rows}).values()), [70.0])

    def test_three_pilots_default(self):
        self.assertEqual(KW.PILOT_PARALLEL, 3)
        picked = [{"item": f"x{i}__t1", "kind": "type"} for i in range(6)]
        self.assertEqual(len(KW.pilot_gate(picked, {}, {}, "s81", {"items": {}})), 3)
        out = KW.pilot_gate(picked, {}, {"pilot_mode": "queue"}, "s81", {"items": {}})
        self.assertEqual((len(out), sum(1 for r in out if r.get("volume"))), (6, 3))


class Expiry(unittest.TestCase):
    def test_owner_silent_expires_and_releases(self):
        c = cfg(act={"LIVE": NOW - 7 * 3600, "OTHER": NOW})
        c["dies"]["s81"]["hold_records"] = [rec()]
        rel = HR.compile_holds(c)
        self.assertEqual(c["dies"]["s81"]["hold_items"], {})
        self.assertEqual(len(rel), 5)
        self.assertTrue(rel[0][2].startswith("EXPIRED"))

    def test_owner_posting_or_renewal_keeps_hold(self):
        c = cfg(act={"LIVE": NOW - 3600, "OTHER": NOW})
        c["dies"]["s81"]["hold_records"] = [rec()]
        HR.compile_holds(c)
        self.assertEqual(len(c["dies"]["s81"]["hold_items"]), 5)
        c = cfg(act={"LIVE": NOW - 9 * 3600, "OTHER": NOW})
        c["dies"]["s81"]["hold_records"] = [rec(owner_since=time.strftime("%Y-%m-%d %H:%M", time.localtime(NOW - 3600)))]
        HR.compile_holds(c)
        self.assertEqual(len(c["dies"]["s81"]["hold_items"]), 5)
        c = cfg(act={"LIVE": NOW - 9 * 3600, "OTHER": NOW})
        c["dies"]["s81"]["hold_records"] = [rec(renewed_at=NOW - 60)]
        HR.compile_holds(c)
        self.assertEqual(len(c["dies"]["s81"]["hold_items"]), 5)

    def test_dead_result_lane_term_expires(self):
        c = cfg(act={"OTHER": NOW})
        c["dies"]["s81"]["hold_records"] = [rec(owner="", release=["result:DEAD-R2:tag"], migrated=True, keys=["a__t1"])]
        HR.compile_holds(c)
        self.assertEqual(c["dies"]["s81"]["hold_items"], {})

    def test_blind_queue_read_never_expires(self):
        c = cfg(act={})
        c["dies"]["s81"]["hold_records"] = [rec()]
        HR.compile_holds(c)
        self.assertEqual(len(c["dies"]["s81"]["hold_items"]), 5)

    def test_legacy_record_without_owner_never_expires(self):
        c = cfg(act={"OTHER": NOW})
        c["dies"]["s81"]["hold_records"] = [rec(owner="", migrated=True, keys=["a__t1"])]
        HR.compile_holds(c)
        self.assertEqual(list(c["dies"]["s81"]["hold_items"]), ["a__t1"])


class NewRecords(unittest.TestCase):
    def test_needs_cause_and_live_owner(self):
        for bad in (rec(cause=""), rec(owner=""), rec(owner="OLD-LANE"), rec(release=["result:OLD-LANE:x"])):
            with self.assertRaises(ValueError, msg=str(bad)):
                HR.add_record(cfg(), "s81", bad)
        HR.add_record(cfg(), "s81", rec())
        HR.add_record(cfg(), "s81", rec(release=["result:OTHER:ok"]))

    def test_registry_alone_is_not_live(self):
        self.assertFalse(HR.lane_known(cfg(), "OLD-LANE", NOW)[0])
        self.assertTrue(HR.lane_known(cfg(), "LIVE", NOW)[0])


class ReleasePilots(unittest.TestCase):
    def setup_cfg(self, passed=(), failed=()):
        c = cfg(items=[f"a__t{i}" for i in range(1, 10)])
        c["dies"]["s81"]["hold_records"] = [rec(owner="LIVE", release=["event_adopt:EVT2"])]
        c["dies"]["s81"]["event"] = "EVT2"
        c["dies"]["s81"]["plan"] = "/x/EVT2.json"
        c["_release_pilot"] = {}
        ctx = HR.Ctx(event_met=KW._hold_term_met, release_pilot_fn=lambda die, it, t0: it in passed,
                     release_pilot_failed_fn=lambda die, it, t0: it in failed)
        return c, ctx

    def test_three_pilots_launch_rest_held(self):
        c, ctx = self.setup_cfg()
        HR.compile_holds(c, ctx)
        held = c["dies"]["s81"]["hold_items"]
        self.assertEqual(len(held), 6)           # 9 released-ready, 3 pilots run, 6 wait
        self.assertEqual(len(c["_release_pilot"]["s81|r1"]["pilots"]), 3)

    def test_first_pass_releases_all(self):
        c, ctx = self.setup_cfg()
        HR.compile_holds(c, ctx)
        pil = c["_release_pilot"]["s81|r1"]["pilots"]
        c2, ctx2 = self.setup_cfg(passed=(pil[1],))
        c2["_release_pilot"] = c["_release_pilot"]
        HR.compile_holds(c2, ctx2)
        self.assertEqual(c2["dies"]["s81"]["hold_items"], {})

    def test_all_pilots_failing_per_instance_releases(self):
        c, ctx = self.setup_cfg()
        HR.compile_holds(c, ctx)
        pil = c["_release_pilot"]["s81|r1"]["pilots"]
        c2, ctx2 = self.setup_cfg(failed=tuple(pil))
        c2["_release_pilot"] = c["_release_pilot"]
        HR.compile_holds(c2, ctx2)
        self.assertEqual(c2["dies"]["s81"]["hold_items"], {})

    def test_one_failed_one_pending_keeps_holding(self):
        c, ctx = self.setup_cfg()
        HR.compile_holds(c, ctx)
        pil = c["_release_pilot"]["s81|r1"]["pilots"]
        c2, ctx2 = self.setup_cfg(failed=(pil[0],))
        c2["_release_pilot"] = c["_release_pilot"]
        HR.compile_holds(c2, ctx2)
        self.assertEqual(len(c2["dies"]["s81"]["hold_items"]), 6)


class PilotDeadlock(unittest.TestCase):
    def pil(self, **k):
        r = {"id": "pilot-s81-aaaaaaaaaaaa", "plan_sha": PLAN, "reason": "PILOT", "release": ["gen_pilot:s81:aaaaaaaaaaaa"],
             "items": ["*"], "pilot_items": ["gunit__t1"], "follow_plan": True, "auto_pilot": True}
        r.update(k)
        return r

    def cfg(self, rows=(), recs=None, sha="a" * 12):
        c = cfg(items=["gunit__t1", "t2", "t3", "t4", "t5"])
        c["dies"]["s81"].update(src_manifest_hash=sha + "0" * 52, hold_records=recs if recs is not None else [self.pil()])
        c["_item_rows"] = list(rows)
        return c

    def test_launchable_pilot_keeps_the_hold(self):
        c = self.cfg()
        HR.compile_holds(c)
        self.assertEqual(c["_pilot_deadlock"], [])
        self.assertIn("*", c["dies"]["s81"]["hold_items"])

    def test_failed_pilot_fails_open(self):
        c = self.cfg(rows=[{"die": "s81", "item": "gunit__t1", "status": "FAIL", "attempt": 6}])
        HR.compile_holds(c)
        self.assertEqual(c["dies"]["s81"]["hold_items"], {})
        self.assertEqual(c["_pilot_deadlock"][0][0:2], ("s81", "pilot-s81-aaaaaaaaaaaa"))
        f = [x for x in HR.audit(c) if x["code"] == "PILOT-DEADLOCK"][0]
        self.assertEqual(sorted(f["items"]), ["gunit__t1", "t2", "t3", "t4", "t5"])                      # WAVE-PILOT-FIX 11-18: the freed items are named
        self.assertEqual(f["n"], 5)

    def test_later_attempt_running_is_not_a_deadlock(self):
        c = self.cfg(rows=[{"die": "s81", "item": "gunit__t1", "status": "FAIL", "attempt": 6},
                           {"die": "s81", "item": "gunit__t1", "status": "RUNNING", "attempt": 7}])
        HR.compile_holds(c)
        self.assertEqual(c["_pilot_deadlock"], [])

    def test_pilot_held_by_another_record_releases(self):
        other = {"id": "o", "plan_sha": PLAN, "reason": "stop list", "release": ["proof:head-serdes-fanout"], "items": ["gunit__t1"], "owner": "LIVE", "cause": "x"}
        c = self.cfg(recs=[self.pil(), other])
        HR.compile_holds(c)
        self.assertNotIn("*", c["dies"]["s81"]["hold_items"])
        self.assertIn("gunit__t1", c["dies"]["s81"]["hold_items"])        # the other record still holds its own item

    def test_stale_tree_record_is_dropped(self):
        c = self.cfg(sha="b" * 12)
        HR.compile_holds(c)
        self.assertEqual(c["dies"]["s81"]["hold_items"], {})
        self.assertIn("names tree aaaaaaaaaaaa", c["_pilot_deadlock"][0][2])

    def test_add_pilot_hold_takes_only_a_launchable_pilot(self):
        c = cfg(items=["gunit__t1", "t2", "t3"])
        d = c["dies"]["s81"]
        d.update(pilot_item="gunit__t1", src_manifest_hash="c" * 64)
        c["_item_names"] = {"s81": ["gunit__t1", "t2", "t3"]}
        c["_item_rows"] = [{"die": "s81", "item": "gunit__t1", "status": "FAIL", "attempt": 3}]
        self.assertTrue(HR.add_pilot_hold(c, "s81", d, {}))
        self.assertEqual(d["hold_records"][-1]["pilot_items"], ["t2"])       # next launchable item
        c2 = cfg(items=["gunit__t1"])
        d2 = c2["dies"]["s81"]
        d2.update(pilot_item="gunit__t1", src_manifest_hash="c" * 64)
        c2["_item_names"] = {"s81": ["gunit__t1"]}
        c2["_item_rows"] = [{"die": "s81", "item": "gunit__t1", "status": "FAIL", "attempt": 3}]
        self.assertFalse(HR.add_pilot_hold(c2, "s81", d2, {}))                # no launchable pilot: fail open, no hold


if __name__ == "__main__":
    unittest.main()
