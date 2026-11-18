#!/usr/bin/env python3
"""PROBE-ONE-1116 / SRC-HEAL-1116 / BINDFETCH-1116 (COORD 11-16)."""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import flow_guard as FG  # noqa: E402
import kit_wave as KW  # noqa: E402

DIE = "qwen_compute"
SD = "CLASS-FAIL ValueError: native clock table"


def opened():
    st = {}
    fams = ["cbf_q11", "coll_n", "cbx_q10__cl1", "slw_st_b_v1__cl2", "slw_st_b_v2__cl3"]
    for i, it in enumerate(fams + [FG.family_of(f) + "__t7" for f in fams]):        # CLASS_N (10) fails open the class
        FG.record_fail(st, DIE, it, "FLOW", SD, now=1000 + i, legacy=False, stage="kit_topology", inp="in1")
    return st


class ProbeOne(unittest.TestCase):
    def test_exactly_one_probe_for_the_whole_class(self):
        st = opened()
        key = FG.held_key(st, DIE, "coll_n")
        self.assertTrue(key.startswith("CLASS"))
        FG.breaker_tick(st, now=5000, inputs={DIE: "in2"})                       # the fix: inputs changed -> probe window
        self.assertEqual(FG.held_key(st, DIE, "cbf_q11", claim=True), "")        # the one probe
        self.assertEqual(FG.held_key(st, DIE, "coll_n", claim=True), "")         # WAVE-PILOT-FIX: probes 2 and 3 (three per class)
        self.assertEqual(FG.held_key(st, DIE, "cbx_q10__cl1", claim=True), "")
        for it in ("slw_st_b_v1__cl2", "slw_st_b_v2__cl3", "cbf_q11__t3"):
            self.assertTrue(FG.held_key(st, DIE, it, claim=True), it)            # no fourth probe
        self.assertEqual(FG.held_key(st, DIE, "cbf_q11", claim=True), "")        # the probe itself stays free

    def test_probe_pass_releases_every_family_in_the_same_tick(self):
        st = opened()
        FG.breaker_tick(st, now=5000, inputs={DIE: "in2"})
        FG.held_key(st, DIE, "cbf_q11", claim=True)
        out = FG.probe_result(st, DIE, "cbf_q11", "place", passed=True)          # got past kit_topology
        self.assertTrue(any("all 5 families released in the same tick" in w for _, w in out), out)
        for it in ("coll_n", "cbx_q10__cl1", "slw_st_b_v1__cl2", "slw_st_b_v2__cl3"):
            self.assertEqual(FG.held_key(st, DIE, it), "", it)
        self.assertFalse(st["flow_guard"]["open"])

    def test_probe_fail_keeps_the_class_shut(self):
        st = opened()
        FG.breaker_tick(st, now=5000, inputs={DIE: "in2"})
        FG.held_key(st, DIE, "cbf_q11", claim=True)
        FG.probe_result(st, DIE, "cbf_q11", "kit_topology", passed=False)
        self.assertTrue(FG.held_key(st, DIE, "coll_n"))
        self.assertEqual(FG.breaker_tick(st, now=6000, inputs={DIE: "in2"}), [])

    def test_a_non_probe_result_does_not_release(self):
        st = opened()
        FG.breaker_tick(st, now=5000, inputs={DIE: "in2"})
        FG.held_key(st, DIE, "cbf_q11", claim=True)
        self.assertEqual(FG.probe_result(st, DIE, "coll_n", "place", passed=True), [])    # coll_n never claimed a probe
        self.assertEqual(FG.held_key(st, DIE, "cbx_q10__cl1", claim=True), "")
        self.assertEqual(FG.held_key(st, DIE, "slw_st_b_v1__cl2", claim=True), "")        # probes 2 and 3 taken
        self.assertTrue(FG.held_key(st, DIE, "coll_n", claim=True))

    def test_config_change_naming_the_class_opens_the_probe_window(self):
        a = KW.breaker_inputs({"dies": {DIE: {"event": "e"}}}, DIE)
        b = KW.breaker_inputs({"dies": {DIE: {"event": "e", "breaker_fix": "kit_topology native clock"}}}, DIE)
        self.assertNotEqual(a, b)
        self.assertEqual(a, KW.breaker_inputs({"dies": {DIE: {"event": "e"}}}, DIE))   # absent key: digest unchanged


class FakeAP:
    def __init__(self):
        self.logs = []

    def log(self, m):
        self.logs.append(m)


class SrcHeal(unittest.TestCase):
    P = "/srv/opentallas-scratch2/claude/kw45/qcbind_pin_e/bind_x/rtl/bind_cells.sv"

    def cfg(self, **kw):
        return {"dies": {DIE: dict({"gen_host": "epyc2", "gen_hosts": ["epyc2", "epyc9", "intel1"]}, **kw)},
                "_src_incomplete": {"epyc9": {DIE: f"{self.P} missing; {self.P[:-3]}2.sv missing; package t: bad"}}}

    def test_copies_missing_files_from_a_whole_host(self):
        calls = []
        done = KW.sync_die_inputs(FakeAP(), self.cfg(), run=lambda argv, inp=None: calls.append(argv[-1]) or 0)
        self.assertEqual(done, [("epyc9", DIE, 2, "epyc2")])         # epyc2 is whole for the die; sorted first
        self.assertEqual(len(calls), 2)                               # the copy, then the verification that the files exist on the target
        self.assertIn("test -e", calls[1])
        self.assertIn("bind_cells.sv", calls[0])
        self.assertIn("--keep-old-files", calls[0])
        self.assertNotIn("package", calls[0])
        self.assertNotRegex(calls[0], r"du -s|-le \d{4}")             # no size limit

    def test_no_whole_host_no_copy(self):
        c = self.cfg()
        c["_src_incomplete"] = {h: {DIE: f"{self.P} missing"} for h in ("epyc2", "epyc9", "intel1")}
        self.assertEqual(KW.sync_die_inputs(FakeAP(), c, run=lambda a, inp=None: 0), [])

    def test_off_switch_and_unsafe_paths(self):
        self.assertEqual(KW.sync_die_inputs(FakeAP(), self.cfg(src_sync=False), run=lambda a, inp=None: 0), [])
        c = self.cfg()
        c["_src_incomplete"] = {"epyc9": {DIE: "/etc/passwd missing; /srv/opentallas-scratch2/claude/../x missing"}}
        self.assertEqual(KW.sync_die_inputs(FakeAP(), c, run=lambda a, inp=None: 0), [])

    def test_failed_copy_is_not_reported(self):
        self.assertEqual(KW.sync_die_inputs(FakeAP(), self.cfg(), run=lambda a, inp=None: 3), [])


class BindFetch(unittest.TestCase):
    def test_no_4gb_skip_in_the_bind_fetch(self):
        src = Path(KW.__file__).read_text()
        i = src.index('_fetch = (f"B={q(bind)}')
        blk = src[i:src.index('rcf, tf = run("bind_fetch"', i)]
        self.assertIn("rsync -a", blk)
        self.assertIn("KW_BIND_COPIED", blk)
        self.assertNotIn("4194304", blk)
        self.assertNotIn("du -sk", blk)
        self.assertFalse(re.search(r"-le\s", blk))


if __name__ == "__main__":
    unittest.main()
