import unittest
import kit_wave as KW

CFG = {"dies": {"d": {"event": "e2"}}}


def row(item, event, q="FAIL", status="ENQUEUED"):
    return {"die": "d", "item": item, "event": event, "status": status, "q_status": q}


class Retire(unittest.TestCase):
    def test_retire_when_current_row_else_relaunch(self):
        st = {"items": {"a1": row("a", "e1"), "a2": row("a", "e2", "RUNNING"),
                        "b1": row("b", "e1"), "c1": row("c", "e1", "SIGNED"), "d1": row("d", "e1", "RUNNING"),
                        "e2": row("e", "e2")}}
        self.assertEqual(KW.retire_superseded_rows(None, CFG, st, now=5), (1, 1))
        it = st["items"]
        self.assertEqual((it["a1"]["status"], it["a1"]["retire"]), ("CANCELLED", "retired"))
        self.assertEqual((it["b1"]["status"], it["b1"]["retire"]), ("CANCELLED", "relaunch"))
        self.assertEqual(it["a1"]["class"], "SUPERSEDED")
        for k in ("a2", "c1", "d1", "e2"):
            self.assertEqual(it[k]["status"], "ENQUEUED", k)      # current event, SIGNED, RUNNING untouched

    def test_dedup_members_of_an_old_event_or_a_retired_owner_are_retired(self):
        st = {"items": {
            "m1": {"die": "d", "item": "m1", "event": "e1", "status": "DEDUP", "dedup_owner": "o1"},
            "m2": {"die": "d", "item": "m2", "event": "e2", "status": "DEDUP", "dedup_owner": "o2"},
            "m3": {"die": "d", "item": "m3", "event": "e2", "status": "DEDUP", "dedup_owner": "o3"},
            "o2": {"die": "d", "item": "o2", "event": "e2", "status": "CANCELLED", "class": "SUPERSEDED"},
            "o3": {"die": "d", "item": "o3", "event": "e2", "status": "RUNNING"}}}
        KW.retire_superseded_rows(None, CFG, st, now=9)
        it = st["items"]
        self.assertEqual((it["m1"]["status"], it["m1"]["retire"]), ("CANCELLED", "dedup"))
        self.assertEqual(it["m2"]["status"], "CANCELLED")
        self.assertEqual(it["m3"]["status"], "DEDUP")                 # current event, live owner: still a member

    def test_idempotent(self):
        st = {"items": {"b1": row("b", "e1")}}
        KW.retire_superseded_rows(None, CFG, st)
        self.assertEqual(KW.retire_superseded_rows(None, CFG, st), (0, 0))


class StalePlan(unittest.TestCase):
    def test_fail_rows_of_names_the_current_plan_lacks_are_retired(self):
        cfg = {"dies": {"s": {"enabled": True, "event": "ev", "plan": "/p/plan.json", "gen_host": "h", "plan_sha256": "c" * 64}}}
        st = {"plans": {"h:/p/plan.json|ev": {"types": ["col_a__t1", "keep__t1"]}}, "items": {
            "x1": {"die": "s", "item": "col_a__t1__cl1__pv2", "status": "FAIL", "event": "ev", "plan_sha": "a" * 64},     # not in plan, old plan sha: retired
            "x2": {"die": "s", "item": "col_a__t1", "status": "FAIL", "event": "ev", "plan_sha": "a" * 64},                # in the plan: kept
            "x3": {"die": "s", "item": "gone__t1", "status": "FAIL", "event": "ev", "plan_sha": "c" * 64},                 # current plan sha: kept (a real failure of this plan)
            "x4": {"die": "s", "item": "gone__t2", "status": "FAIL", "event": "ev", "plan_sha": ""},                       # unknown block: kept
            "x5": {"die": "s", "item": "gone__t3", "status": "SIGNED", "event": "ev", "plan_sha": "a" * 64}}}               # not a FAIL: untouched
        KW.retire_superseded_rows(None, cfg, st, now=7)
        got = {k: (r["status"], r.get("retire")) for k, r in st["items"].items()}
        self.assertEqual(got["x1"], ("CANCELLED", "stale-plan"))
        self.assertEqual([got[k][0] for k in ("x2", "x3", "x4", "x5")], ["FAIL", "FAIL", "FAIL", "SIGNED"])
        self.assertEqual(st["items"]["x1"]["class"], "SUPERSEDED")
        cfg["dies"]["s"]["enabled"] = False                      # unknown plan names: nothing retired
        st2 = {"plans": {}, "items": {"y": {"die": "s", "item": "z", "status": "FAIL", "plan_sha": "a" * 64}}}
        KW.retire_superseded_rows(None, cfg, st2)
        self.assertEqual(st2["items"]["y"]["status"], "FAIL")


class ResultHeader(unittest.TestCase):
    def test_result_without_the_arrow_releases_but_a_cc_does_not(self):
        f = KW.result_pass_fn(["- 2026-11-17 19:01 PST RESULT [S81-DIE-R3] d6b-applied PASS: D6z APPLIED",
                               "- 2026-11-17 19:17 PST RESULT [S81-TYPES-R3 -> COORD] col-wave2 PASS: ok",
                               "- 2026-11-17 19:20 PST RESULT [OTHER -> COORD; cc S81-FOO] foo-tag PASS"])
        self.assertTrue(f("S81-DIE-R3", "d6b-applied"))
        self.assertTrue(f("S81-TYPES-R3", "col-wave2"))
        self.assertFalse(f("S81-FOO", "foo-tag"))                # a cc'd lane is not the sender
        self.assertFalse(f("S81-DIE-R3", "col-wave2"))


class StaleEvent(unittest.TestCase):
    def test_fail_rows_on_an_old_event_are_history(self):
        cfg = {"dies": {"d": {"enabled": True, "event": "e2"}, "p": {"enabled": True, "event": "x", "retire_stale_event_fails": False}}}
        st = {"items": {"a": {"die": "d", "item": "a", "event": "e1", "status": "FAIL", "reason": "boom"},
                        "b": {"die": "d", "item": "b", "event": "e2", "status": "FAIL"},
                        "c": {"die": "d", "item": "c", "event": "e1", "status": "SIGNED"},
                        "e": {"die": "p", "item": "e", "event": "old", "status": "FAIL"}}}
        KW.retire_superseded_rows(None, cfg, st, now=3)
        got = {k: (r["status"], r.get("retire")) for k, r in st["items"].items()}
        self.assertEqual(got["a"], ("CANCELLED", "stale-event"))
        self.assertIn("boom", st["items"]["a"]["reason"])
        self.assertEqual([got[k][0] for k in "bce"], ["FAIL", "SIGNED", "FAIL"])


class SignedAndOldPlan(unittest.TestCase):
    def test_old_plan_route_hold_is_retired_and_signed_rows_are_not_counted_as_waiting(self):
        import under_use as UU
        cfg = {"dies": {"d": {"enabled": True, "event": "e2"}}}
        st = {"items": {"a": {"die": "d", "item": "a", "event": "e1", "status": "ROUTE-HELD", "route_hold": "SKIP-OLDPLAN: attempt of plan x"},
                        "b": {"die": "d", "item": "b", "event": "e1", "status": "ROUTE-HELD", "route_hold": "WAIT-FORM: visual"}}}
        KW.retire_superseded_rows(None, cfg, st, now=4)
        self.assertEqual((st["items"]["a"]["status"], st["items"]["a"]["retire"]), ("CANCELLED", "oldplan-route-hold"))
        self.assertEqual(st["items"]["b"]["status"], "ROUTE-HELD")                     # an owner-review hold stays
        items = {"s": {"die": "d", "item": "s", "event": "e1", "status": "ENQUEUED", "q_status": "SIGNED"},
                 "w": {"die": "d", "item": "w", "event": "e2", "status": "ENQUEUED", "q_status": "QUEUED"}}
        cls = UU.row_classes(items, cfg)
        self.assertNotIn("s", cls)
        self.assertIn("w", cls)
