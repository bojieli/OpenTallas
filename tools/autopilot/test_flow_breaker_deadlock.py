"""WAVE-PILOT-FIX 11-17 (COORD): the FLOW-GUARD breaker cannot deadlock a family: 3 probes per class, a probe running 60 min counts as a pass,
a tree switch resets the failures that predate it, a launch only goes to a host that holds the item's tree."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import flow_guard as FG  # noqa: E402
import kit_wave as KW  # noqa: E402

KEY = "CLASS qwen_compute|kit_rtl|FLOW: x"


def state(**e):
    ent = {"die": "qwen_compute", "fams": ["a", "b", "c", "d"], "state": "probe", "stage": "kit_rtl", "inp": "i1", "inp_probe": "i2", "t": 1000.0, "last_fail": 1000.0}
    ent.update(e)
    return {"flow_guard": {"open": {KEY: ent}, "last": {}, "last2": {}, "probation": {}, "fails": [], "pf_posted": {}, "paths": {}, "trees": {}, "refused": []}}


class Probes(unittest.TestCase):
    def test_three_probes_then_held(self):
        st = state()
        self.assertEqual([FG.held_key(st, "qwen_compute", f"{f}__t1", claim=True) for f in "abc"], ["", "", ""])
        self.assertEqual(FG.held_key(st, "qwen_compute", "d__t1", claim=True), KEY)       # the 4th item of the class waits
        self.assertEqual(FG.probe_items(st["flow_guard"]["open"][KEY]), ["a__t1", "b__t1", "c__t1"])
        self.assertEqual(FG.held_key(st, "qwen_compute", "b__t1"), "")                    # a probe is never held by its own class

    def test_one_probe_passing_releases_the_class(self):
        st = state()
        for f in "abc":
            FG.held_key(st, "qwen_compute", f"{f}__t1", claim=True)
        FG.probe_result(st, "qwen_compute", "b__t1", "place", passed=True)
        self.assertEqual(st["flow_guard"]["open"], {})

    def test_two_failed_probes_shut_the_class_die_wide_until_the_cause_changes(self):
        st = state()
        for f in "abc":
            FG.held_key(st, "qwen_compute", f"{f}__t1", claim=True)
        FG.probe_result(st, "qwen_compute", "a__t1", "kit_rtl", passed=False, failed_stage=True)
        self.assertEqual(st["flow_guard"]["open"][KEY]["state"], "probe")                 # one failed probe: the others still run
        FG.probe_result(st, "qwen_compute", "b__t1", "kit_rtl", passed=False, failed_stage=True)
        self.assertEqual(st["flow_guard"]["open"][KEY]["state"], "shut")                  # two failed probes: shut (WAVE-PILOT-FIX 11-18)
        for f in "abcd":                                                                 # die-wide: every family, the third probe included
            self.assertEqual(FG.held_key(st, "qwen_compute", f"{f}__t9", claim=True), KEY)
        self.assertEqual(FG.breaker_tick(st, 1.0, {"qwen_compute": "i2"}), [])             # same inputs as the failed probes: stays shut
        rel = FG.breaker_tick(st, 2.0, {"qwen_compute": "i3"})                             # the cause changed: a new probe window
        self.assertTrue(rel and "PROBE" in rel[0][1])

    def test_probe_running_60_min_is_not_a_pass(self):
        st = state()
        FG.held_key(st, "qwen_compute", "a__t1", claim=True)
        t0 = st["flow_guard"]["open"][KEY]["probe_t"]["a__t1"]
        self.assertEqual(FG.breaker_tick(st, t0 + 7200, {"qwen_compute": "i2"}), [])
        self.assertIn(KEY, st["flow_guard"]["open"])                                    # a timeout never closes the class
        self.assertEqual(FG.held_key(st, "qwen_compute", "d__t1", claim=True), "")       # still within the three probe slots
        self.assertEqual(FG.held_key(st, "qwen_compute", "b__t1", claim=True), "")
        self.assertEqual(FG.held_key(st, "qwen_compute", "c__t1", claim=True), KEY)      # the fourth waits

    def test_failed_probe_does_not_count_as_a_pass(self):
        st = state()
        FG.held_key(st, "qwen_compute", "a__t1", claim=True)
        t0 = st["flow_guard"]["open"][KEY]["probe_t"]["a__t1"]
        FG.probe_result(st, "qwen_compute", "a__t1", "kit_rtl", passed=False, failed_stage=True)
        FG.breaker_tick(st, t0 + 4000, {"qwen_compute": "i2"})
        self.assertIn(KEY, st["flow_guard"]["open"])


class TreeSwitch(unittest.TestCase):
    def test_switch_opens_the_probe_window_of_that_die_only_and_closes_nothing(self):
        st = state(state="shut")
        st["flow_guard"]["open"]["CLASS s81|x"] = dict(st["flow_guard"]["open"][KEY], die="s81")
        self.assertEqual(FG.breaker_tick(st, 5000.0, {}, {"qwen_compute": "/t/d3", "s81": "/s/a"}), [])   # first sight: recorded only
        rel = FG.breaker_tick(st, 5100.0, {"qwen_compute": "i9"}, {"qwen_compute": "/t/d4", "s81": "/s/a"})
        self.assertEqual([k for k, _ in rel], [KEY])
        self.assertEqual(sorted(st["flow_guard"]["open"]), sorted([KEY, "CLASS s81|x"]))                # nothing closed
        self.assertEqual(st["flow_guard"]["open"][KEY]["state"], "probe")
        self.assertEqual(st["flow_guard"]["open"]["CLASS s81|x"]["state"], "shut")


class TreeHost(unittest.TestCase):
    class AP:
        HUB_NAME = "hub"

        def __init__(self, have):
            self.have, self.calls = have, []

        def sh(self, argv, timeout=None, input=None):
            host = argv[argv.index("ControlPath=none") + 1] if "ControlPath=none" in argv else "hub"
            self.calls.append(host)
            return (0 if host in self.have else 1), "", ""

    def cfg(self):
        return {"_hub": "hub", "dies": {"qwen_compute": {"gen_host": "epyc8", "gen_hosts": ["epyc8", "epyc9"]}}}

    def test_host_without_the_tree_is_replaced_or_deferred(self):
        ap = self.AP({"epyc9"})
        sp = {"gen_host": "epyc10", "src": "/t/d4"}
        self.assertEqual(KW.tree_host_for(ap, self.cfg(), "qwen_compute", sp, "glue"), "epyc9")
        ap2 = self.AP(set())
        self.assertEqual(KW.tree_host_for(ap2, self.cfg(), "qwen_compute", dict(sp), "glue"), "")

    def test_host_with_the_tree_is_kept_and_probed_once(self):
        ap = self.AP({"epyc8"})
        c = self.cfg()
        sp = {"gen_host": "epyc8", "src": "/t/d4"}
        self.assertEqual(KW.tree_host_for(ap, c, "qwen_compute", sp, "a"), "epyc8")
        KW.tree_host_for(ap, c, "qwen_compute", sp, "b")
        self.assertEqual(ap.calls, ["epyc8"])

    def test_unknown_probe_result_never_refuses(self):
        class Bad(self.AP):
            def sh(self, argv, timeout=None, input=None):
                return 255, "", ""
        self.assertEqual(KW.tree_host_for(Bad(set()), self.cfg(), "qwen_compute", {"gen_host": "epyc10", "src": "/t"}, "x"), "epyc10")


if __name__ == "__main__":
    unittest.main()
