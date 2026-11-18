"""WAVE-PILOT-FIX 11-17 (COORD): replay the S81 dsdv_slice_*_C sequence of 14:20-15:03: a batch of retried attempts launched at once all failed the
same KIT_PREFLIGHT class because the verdict arrives ~2 h later.  A die's retried attempts launch at most 3 at a time."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import flow_guard as FG  # noqa: E402
import kit_wave as KW  # noqa: E402

ITEMS = ["dsdv_slice_c1x_C__t1", "dsdv_slice_c1x_C__t3", "dsdv_slice_c1x_C__t4", "dsdv_slice_c1x_C__t5", "dsdv_slice_c1x_C__t6", "dsdv_slice_c1x_C__t10",
         "dsdv_slice_iq_C__t1", "dsdv_slice_lepe_mu_C__t1", "dsdv_slice_lepe_nh_mus_C__t1", "dsdv_slice_lepw_mus_C__t1", "dsdv_slice_c3x_C__t1"]


def cfg(event="3fa87b84b18"):
    return {"dies": {"s81": {"event": event, "src_sha": "d5e", "_plan_sha": "p1", "kit_rtl": {}}}}


def state():
    st = {"items": {}}
    for i, it in enumerate(ITEMS):          # each item's last attempt failed earlier (src_manifest / kit_snap / kit_rtl)
        st["items"][f"s81|{it}|b1"] = {"die": "s81", "item": it, "attempt": 5, "status": "FAIL", "class": "FLOW", "stage": "kit_snap", "started": 1000.0 + i}
    return st


def replay(c, st, todo):
    """the wave's launch loop: gate each pick, launch (a RUNNING row, attempt+1) when it passes"""
    out = []
    for it in todo:
        why = KW.retry_probe_defer(c, st, "s81", {"item": it})
        if why:
            continue
        prev = max((x for x in st["items"].values() if x["item"] == it), key=lambda x: x["attempt"])
        st["items"][f"s81|{it}|b{prev['attempt'] + 1}"] = {"die": "s81", "item": it, "attempt": prev["attempt"] + 1, "status": "RUNNING", "started": KW.time.time() + len(st["items"])}
        out.append(it)
    return out


class RetryProbe(unittest.TestCase):
    def test_the_1420_sequence_launches_at_most_three(self):
        c, st = cfg(), state()
        first = replay(c, st, ITEMS)
        self.assertEqual(len(first), 3)                            # 11 retried items in one tick: 3 launch
        self.assertEqual(len(replay(c, st, [i for i in ITEMS if i not in first])), 0)   # a later tick, nothing has passed place: still 3 in flight

    def test_a_retried_attempt_past_place_releases_the_rest(self):
        c, st = cfg(), state()
        first = replay(c, st, ITEMS)
        k = [k for k, v in st["items"].items() if v["item"] == first[0] and v["attempt"] == 6][0]
        st["items"][k]["status"] = "ENQUEUED"                       # one probe got past place
        self.assertEqual(len(replay(c, st, [i for i in ITEMS if i not in first])), 8)

    def test_a_failed_probe_frees_a_slot(self):
        c, st = cfg(), state()
        first = replay(c, st, ITEMS)
        k = [k for k, v in st["items"].items() if v["item"] == first[0] and v["attempt"] == 6][0]
        st["items"][k]["status"] = "FAIL"
        self.assertEqual(len(replay(c, st, [i for i in ITEMS if i not in first])), 1)

    def test_an_input_change_starts_a_new_cohort(self):
        c, st = cfg(), state()
        replay(c, st, ITEMS)
        c2 = cfg(event="newevent")                                   # the fix: inputs changed
        for v in st["items"].values():
            if v["status"] == "RUNNING":
                v["status"] = "FAIL"
        self.assertEqual(len(replay(c2, st, ITEMS)), 3)

    def test_first_attempts_and_non_failed_rows_are_never_limited(self):
        c, st = cfg(), {"items": {}}
        self.assertTrue(all(KW.retry_probe_defer(c, st, "s81", {"item": i}) == "" for i in ITEMS))
        c, st = cfg(), state()
        for v in st["items"].values():
            v["status"] = "RUNNING"
        self.assertTrue(all(KW.retry_probe_defer(c, st, "s81", {"item": i}) == "" for i in ITEMS))

    def test_die_option_turns_it_off(self):
        c, st = cfg(), state()
        c["dies"]["s81"]["retry_probe"] = False
        self.assertEqual(len(replay(c, st, ITEMS)), len(ITEMS))


KEY = "CLASS s81|place|FLOW: kit recipe / preflight @place: KIT_PREFLIGHT FAIL issues N"


def breaker(state="shut"):
    return {"flow_guard": {"open": {KEY: {"die": "s81", "state": state, "stage": "place", "inp": "i1", "inp_probe": "i1", "t": 100.0, "last_fail": 100.0,
                                          "kind": "", "n": 12, "fams": ["dsdv_slice_c1x_C", "dsdv_slice_iq_C"], "probe": {}}},
                           "last": {}, "last2": {}, "probation": {}, "fails": [], "pf_posted": {}, "paths": {}, "trees": {}, "refused": []}}


class BreakerClosesOnlyOnAPlacePass(unittest.TestCase):
    """FABLE-FLOW-1700: the breaker released twice without a pass (42 s after opening; on a probe timeout)."""

    def test_inputs_changing_42_s_after_opening_only_opens_the_probe_window(self):
        st = breaker()
        rel = FG.breaker_tick(st, 142.0, {"s81": "i2"})                                    # class opened at t=100, inputs change 42 s later
        self.assertTrue(rel and "PROBE" in rel[0][1])
        self.assertIn(KEY, st["flow_guard"]["open"])                                       # still open: not a release
        self.assertEqual(st["flow_guard"]["open"][KEY]["state"], "probe")
        launched = [n for n in range(1, 9) if FG.held_key(st, "s81", "dsdv_slice_c1x_C__t%d" % n, claim=True) == ""]
        self.assertEqual(len(launched), 3)                                                 # three probes, then the family waits

    def test_probe_timeout_is_no_pass(self):
        st = breaker("probe")
        for i in ("a", "b", "c"):
            FG.held_key(st, "s81", "dsdv_slice_c1x_C__t" + i, claim=True)
        t0 = max(st["flow_guard"]["open"][KEY]["probe_t"].values())
        self.assertEqual(FG.breaker_tick(st, t0 + 3 * 3600, {"s81": "i1"}), [])           # 3 h without a result
        self.assertIn(KEY, st["flow_guard"]["open"])
        self.assertTrue(FG.held_key(st, "s81", "dsdv_slice_c1x_C__tz", claim=True))        # siblings stay held

    def test_only_a_probe_passing_place_closes_the_class(self):
        st = breaker("probe")
        FG.held_key(st, "s81", "dsdv_slice_c1x_C__ta", claim=True)
        FG.held_key(st, "s81", "dsdv_slice_c1x_C__tb", claim=True)
        FG.probe_result(st, "s81", "dsdv_slice_c1x_C__ta", "gen", passed=False, failed_stage=True)      # one probe fails earlier than place
        self.assertIn(KEY, st["flow_guard"]["open"])
        out = FG.probe_result(st, "s81", "dsdv_slice_c1x_C__tb", "place", passed=True)
        self.assertTrue(any("released" in w for _, w in out))
        self.assertNotIn(KEY, st["flow_guard"]["open"])


if __name__ == "__main__":
    unittest.main()
