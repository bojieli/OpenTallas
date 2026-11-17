"""HOLD-FLOW-R 11-16 (FABLE-FLOW-2000): dead hold terms.  (a) a record is refused unless each term resolves to a planned/adopted plan
event, a live lane by exact name, or a known check; (b) a held term with no producer for 12 h is an alert; matcher variants."""
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hold_records as HR  # noqa: E402

PLAN = "p" * 64
NOW = time.mktime(time.strptime("2026-11-16 20:00", "%Y-%m-%d %H:%M"))


def cfg(**extra):
    c = {"dies": {"qwen_compute": {"event": "s29q103S4Q9KF", "plan": "/p/zz_s29_qc103_s4q9kf.json", "plan_sha256": PLAN,
                                   "planned_events": ["S4q9l2", "S4q9l2d", "S4q9m"],
                                   "hold_event_items": {PLAN: ["a__t1", "b__t1"]}}},
         "_registry_lanes": {"QC-PLAN-R", "S81-TYPES-R2"},
         "_lane_activity": {"FABLE-FIX-S81-SVC": NOW - 3600, "S81-BKSEL-O": NOW - 30 * 3600, "OLD-LANE": NOW - 400 * 3600}}
    c.update(extra)
    return c


def rec(term, **k):
    r = {"id": "r1", "plan_sha": PLAN, "reason": "why", "release": [term], "items": ["a__t1"]}
    r.update(k)
    return r


def accepted(term, c=None):
    c = c or cfg()
    try:
        HR.add_record(c, "qwen_compute", rec(term))
        return True
    except ValueError:
        return False


class WriteGuard(unittest.TestCase):
    def test_lane_terms_need_a_live_lane_by_exact_name(self):
        self.assertTrue(accepted("result:QC-PLAN-R:kf-ready"))            # registry
        self.assertTrue(accepted("result:FABLE-FIX-S81-SVC:svc-ready"))   # posted 1 h ago
        self.assertTrue(accepted("result:S81-BKSEL-O:bksel"))             # posted 30 h ago, inside 48 h
        self.assertFalse(accepted("result:OLD-LANE:x"))                   # silent for 400 h
        self.assertFalse(accepted("result:NO-SUCH-LANE:x"))
        self.assertFalse(accepted("result:qc-plan-r:kf-ready"))           # case variant is not the lane
        with self.assertRaisesRegex(ValueError, "did you mean 'QC-PLAN-R'"):
            HR.add_record(cfg(), "qwen_compute", rec("result:qc-plan-r:kf-ready"))

    def test_unreadable_registry_never_refuses(self):
        c = cfg()
        c.pop("_registry_lanes")
        self.assertTrue(accepted("result:ANY-LANE:x", c))

    def test_events_must_be_planned_or_adopted(self):
        for ok in ("event_adopt:S4q9l2", "event_adopt:s4Q9L2", "event_adopt:S4q9m", "event_adopt:S4q9kf", "event_adopt:s4q9l2*"):
            self.assertTrue(accepted(ok), ok)
        for bad in ("event_adopt:S4q9z", "event_adopt:S4q9", "event_adopt:Event F"):
            self.assertFalse(accepted(bad), bad)

    def test_suffix_variant_error_names_the_variants(self):
        c = cfg()
        c["dies"]["qwen_compute"]["planned_events"] = ["S4q9l2d"]
        with self.assertRaisesRegex(ValueError, r"known variants \['s4q9l2d'\]"):
            HR.add_record(c, "qwen_compute", rec("event_adopt:S4q9l2"))
        self.assertTrue(accepted("event_adopt:S4q9l2*", c))               # explicit prefix
        self.assertTrue(accepted("event_adopt:S4q9l2d", c))

    def test_system_checks_are_known(self):
        c = cfg()
        c["dies"]["x"] = {}
        self.assertTrue(accepted("lint_clean:qwen_compute"))
        self.assertTrue(accepted("digest_changed"))
        self.assertFalse(accepted("lane_ready:HEAD-99"))                   # free text


class Matcher(unittest.TestCase):
    """exact name, case-insensitive, whole token: S4q9l2 never fires on S4q9l2d (and the audit says so)"""

    def met(self, term, event, plan=""):
        c = cfg()
        c["dies"]["qwen_compute"].update(event=event, plan=plan)
        return HR.term_met(term, {}, "qwen_compute", "a__t1", c, HR.Ctx())

    def test_case_and_suffix(self):
        self.assertTrue(self.met("event_adopt:S4q9l2", "s4q9l2"))
        self.assertTrue(self.met("event_adopt:S4q9l2", "zz_S4Q9L2"))
        self.assertFalse(self.met("event_adopt:S4q9l2", "s4q9l2d"))        # suffix variant: different event
        self.assertFalse(self.met("event_adopt:S4q9l2d", "s4q9l2"))
        self.assertTrue(self.met("event_adopt:S4q9l2*", "s4q9l2d"))
        self.assertTrue(self.met("event_adopt:S4q9kf", "s29q103S4Q9KF", "/p/zz_s29_qc103_s4q9kf.json"))   # the plan file token fires

    def test_audit_flags_the_variant(self):
        c = cfg()
        HR.add_record(c, "qwen_compute", rec("event_adopt:S4q9l2"))
        HR.compile_holds(c)
        codes = {f["code"] for f in HR.audit(c)}
        self.assertIn("TERM-VARIANT", codes)
        self.assertNotIn("TERM-UNREACHABLE", codes)


class Alerts(unittest.TestCase):
    def held(self, terms):
        c = cfg(_queue_recent=[])
        c["_hold_rec_info"] = {"qwen_compute": [dict(id="r1", release=terms, held=3, stale=False, zero=False, plan_sha=PLAN)]}
        c["dies"]["qwen_compute"]["hold_records"] = [rec(terms[0], release=terms)]
        return c

    def test_no_producer_for_12h_alerts_once_old_enough(self):
        c = self.held(["result:OLD-LANE:x", "event_adopt:S4q9m", "lint_clean:qwen_compute", "proof:NOPE"])
        seen = {}
        self.assertEqual(HR.term_alerts(c, seen, now=NOW), [])                 # first sighting: clock starts
        self.assertEqual(len(seen), 2)                                         # OLD-LANE result, proof:NOPE
        al = HR.term_alerts(c, seen, now=NOW + 11 * 3600)
        self.assertEqual(al, [])
        al = HR.term_alerts(c, seen, now=NOW + 12.5 * 3600)
        self.assertEqual(sorted(a["term"] for a in al), ["proof:NOPE", "result:OLD-LANE:x"])
        self.assertTrue(all(a["since_h"] >= 12 and a["n"] == 3 for a in al))

    def test_a_producer_or_a_met_term_resets_the_clock(self):
        c = self.held(["result:OLD-LANE:x"])
        seen = {}
        HR.term_alerts(c, seen, now=NOW)
        c["_lane_activity"]["OLD-LANE"] = NOW + 3600                            # the lane posted: it is a producer again
        self.assertEqual(HR.term_alerts(c, seen, now=NOW + 13 * 3600), [])
        self.assertEqual(seen, {})
        c["_lane_activity"]["OLD-LANE"] = 0
        HR.term_alerts(c, seen, now=NOW + 14 * 3600)
        self.assertEqual(HR.term_alerts(c, seen, now=NOW + 40 * 3600, is_met=lambda *a: True), [])

    def test_proof_named_in_a_recent_post_has_a_producer(self):
        c = self.held(["proof:DRT0255"])
        c["_queue_recent"] = ["- 2026-11-16 19:00 PST RESULT [QC-PINACCESS-O -> COORD] DRT0255 run started"]
        seen = {}
        HR.term_alerts(c, seen, now=NOW)
        self.assertEqual(seen, {})

    def test_kit_wave_wires_the_check(self):
        src = (Path(__file__).resolve().parent / "kit_wave.py").read_text()
        self.assertIn("HR.term_alerts(", src)
        self.assertIn("hold terms with no producer for 12 h", src)
        self.assertIn('"TERM-VARIANT"', src)
        self.assertIn("_registry_lanes", src)


if __name__ == "__main__":
    unittest.main()
