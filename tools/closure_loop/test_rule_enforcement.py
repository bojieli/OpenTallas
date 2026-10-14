"""RULE ENFORCEMENT (owner 2026-10-13, el1013-rule-enforcement).
1. Measured clock rule: > 15,000 sinks on one clock root is REFUSED unless the kit's --cts gate measured TT insertion
   <= 300 ps and leaf spread <= 80 ps; a declared spine or a spec waiver does not waive it; CLOSED tiles stand.
2. Structure-repeat limit: >= 2 terminal failed routes of a block since its last CLOSED need "structural_change"."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("CL_STATE", tempfile.mkdtemp(prefix="ruleenf_"))
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE.parent / "ref_tile")]
import closure_loop as cl  # noqa: E402
import pre_route_gate as PG  # noqa: E402
import textbook_lint as TL  # noqa: E402

GOOD = {"max_root_sinks": 48000, "tt_insertion_ps": 250.0, "tt_spread_ps": 60.0}


def lint_res(n):
    return {"findings": {}, "refuse": {}, "metrics": {"clock_max_root_sinks": n, "clock_max_root": "port:ck"}}


def gate_out(n, lo=None, hi=None):
    s = f"GATE_TB textbook_lint: INFO clock_roots max_root_sinks={n} root=port:ck rule=FAIL: x\nGATE_CTS_RC=0\n"
    if hi is not None:
        s += (f"GATE_CK ss insertion all 300.0..420.0 ps (spread 120.0), boundary mean 350; tt insertion all "
              f"{lo}..{hi} ps (spread {round(hi - lo, 1)}), boundary mean 200; macro_clk flag None\n")
    return s


class ClockRule(unittest.TestCase):
    def test_constants_are_the_owner_numbers(self):
        self.assertEqual((TL.CLK_ROOT_SINKS_MAX, TL.CLK_INSERTION_MAX_PS, TL.CLK_SPREAD_MAX_PS), (15000, 300.0, 80.0))

    def test_rule(self):
        self.assertTrue(TL.clock_rule(15000)[0])
        self.assertFalse(TL.clock_rule(15001)[0])                                   # no evidence
        self.assertTrue(TL.clock_rule(48000, GOOD)[0])
        self.assertTrue(TL.clock_rule(48000, dict(GOOD, tt_insertion_ps=300.0, tt_spread_ps=80.0))[0])
        self.assertFalse(TL.clock_rule(48000, dict(GOOD, tt_insertion_ps=300.1))[0])
        self.assertFalse(TL.clock_rule(48000, dict(GOOD, tt_spread_ps=80.1))[0])
        self.assertFalse(TL.clock_rule(48000, dict(GOOD, tt_spread_ps=None))[0])    # one number missing
        self.assertFalse(TL.clock_rule(48000, dict(GOOD, max_root_sinks=20000))[0])  # evidence of another netlist
        self.assertIn("250.0 ps", TL.clock_rule(48000, GOOD)[1])
        self.assertIn("60.0 ps", TL.clock_rule(100, GOOD)[1])                       # measured numbers always reported

    def test_lint_refuses_in_every_mode_and_ignores_waivers(self):
        for mode in ("warn", "refuse"):
            r = TL.verdict(lint_res(48000), mode, waive=("clock_sinks", "clock_domain"), refuse_checks=(),
                           clock={"enforce": True})
            self.assertEqual((r["verdict"], r["refusing_checks"]), ("REFUSE", ["clock_sinks"]), mode)
            self.assertIn("hardened leaves", r["refuse"]["clock_sinks"][0])

    def test_lint_evidence_closed_and_small(self):
        self.assertEqual(TL.verdict(lint_res(48000), "refuse", clock={"enforce": True, "evidence": GOOD})["verdict"], "PASS")
        bad = dict(GOOD, tt_insertion_ps=410.0)
        self.assertEqual(TL.verdict(lint_res(48000), "refuse", clock={"enforce": True, "evidence": bad})["verdict"], "REFUSE")
        r = TL.verdict(lint_res(48000), "refuse", clock={"enforce": True, "closed_stands": True})
        self.assertEqual(r["verdict"], "PASS")                                      # CLOSED tiles are not re-judged
        self.assertEqual(TL.verdict(lint_res(15000), "refuse", clock={"enforce": True})["verdict"], "PASS")
        r = TL.verdict(lint_res(48000), "refuse")                                   # gate's own run: WARN, gate judges
        self.assertEqual((r["verdict"], r["refusing_checks"]), ("WARN", []))

    def test_hard_children_count_one_sink_each(self):
        v = """module top(input ck, input d, output q);
  wire n1;
  DFFHQNx1_ASAP7_75t_R f0 (.CLK(ck), .D(d), .QN(n1));
  DFFHQNx1_ASAP7_75t_R f1 (.CLK(ck), .D(n1), .QN(q));
  ot_leaf_hard u_leaf0 (.clk(ck), .a(d));
  ot_leaf_hard u_leaf1 (.clk(ck), .a(n1));
endmodule
"""
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "n.v"
            p.write_text(v)
            r = TL.run(str(p), None)
        self.assertEqual(r["metrics"]["clock_max_root_sinks"], 4)    # 2 flops + 2 hard-child clock pins
        self.assertTrue(r["clock_rule"]["ok"])


class GateClock(unittest.TestCase):
    def item(self, out, cts, spec=None):
        g = PG.Gate()
        PG.clock_item(g, PG.clock_record(out, cts, spec))
        return g, [i for i in g.items if i["check"] == "clock_rule"][0]

    def test_small_root_passes_and_reports_measurement(self):
        g, it = self.item(gate_out(9000, 150.0, 190.0), True)
        self.assertEqual(it["severity"], "INFO")
        self.assertIn("insertion 190.0 ps, leaf spread 40.0 ps", it["message"])

    def test_big_root_without_cts_fails(self):
        g, it = self.item(gate_out(48000), False)
        self.assertEqual((g.verdict, it["severity"]), ("FAIL", "FAIL"))
        self.assertIn("without --cts", it["message"])

    def test_declared_spine_does_not_waive(self):
        g, it = self.item(gate_out(48000), True, {"clock": "spine"})
        self.assertEqual(it["severity"], "FAIL")
        self.assertIn("does not waive", it["message"])

    def test_big_root_passes_only_on_measured_numbers(self):
        g, it = self.item(gate_out(48000, 210.0, 280.0), True, {"clock": "spine"})
        self.assertEqual(it["severity"], "INFO")
        self.assertEqual((g.clock["tt_insertion_ps"], g.clock["tt_spread_ps"], g.clock["verdict"]), (280.0, 70.0, "PASS"))
        for lo, hi in ((250.0, 320.0), (190.0, 290.0)):               # insertion miss; spread miss
            g, it = self.item(gate_out(48000, lo, hi), True)
            self.assertEqual(it["severity"], "FAIL", (lo, hi))

    def kit(self, td, clock=None):
        kd = Path(td) / "kit"
        kd.mkdir(exist_ok=True)
        if clock is not None:
            import hashlib
            payload = b"module fixture; endmodule\n"
            (kd / "fixture.v").write_bytes(payload)
            entries = [{"path": "kit/fixture.v", "kind": "file", "sha256": hashlib.sha256(payload).hexdigest(),
                        "git_blob": PG.SB.blob_hash(payload), "source": "working_tree"}]
            binding = {"schema": PG.SB.SCHEMA, "files": entries, "manifest_sha256": PG.SB.canonical_digest(entries),
                       "remote_archive_verified": True}
            (kd / PG.CLOCK_RESULT).write_text(json.dumps({"clock": clock, "source_binding": binding}))
        return kd

    def test_submit_side(self):
        with tempfile.TemporaryDirectory() as td, patch.object(PG, "ROOT", None):
            PG.ROOT = Path(td)
            sev = lambda kd, **kw: (lambda g: (PG.check_clock_evidence(g, kd, **kw), g.verdict)[1])(PG.Gate())  # noqa: E731
            self.assertEqual(sev(self.kit(td)), "PASS")                            # nothing known: in-flow lint judges
            self.assertEqual(sev(self.kit(td), known_sinks=48000), "FAIL")         # history says big, no evidence
            self.assertEqual(sev(self.kit(td), known_sinks=48000, closed_stands=True), "PASS")
            self.assertEqual(sev(self.kit(td), known_sinks=9000), "PASS")
            self.assertEqual(sev(self.kit(td, GOOD), known_sinks=48000), "PASS")   # measured evidence in the kit
            self.assertEqual(sev(self.kit(td, dict(GOOD, tt_spread_ps=95.0))), "FAIL")
            self.assertEqual(sev(self.kit(td, dict(GOOD, tt_insertion_ps=None, tt_spread_ps=None))), "FAIL")
            small = {"max_root_sinks": 9000, "tt_insertion_ps": None, "tt_spread_ps": None}
            self.assertEqual(sev(self.kit(td, small), known_sinks=48000), "PASS")  # rebuilt tile proved itself

    def test_known_sinks_from_history(self):
        old = ("textbook_lint: WARN clock_domain: clock root port clk: 48,485 flops > 15,000 on one root (+0 ICGs, "
               "18 macro clock pins; e.g. base_q[0]): split")
        jobs = [dict(name="a", updated="2026-10-12T01:00:00-07:00", textbook_lint={"lines": [old]}),
                dict(name="b", updated="2026-10-11T01:00:00-07:00",
                     textbook_lint={"lines": ["textbook_lint: INFO clock_roots max_root_sinks=900 root=port:ck"]}),
                dict(name="c", updated="2026-10-13T01:00:00-07:00")]
        self.assertEqual(cl.known_clock_sinks(jobs), 48503)
        self.assertEqual(cl.known_clock_sinks(jobs[1:]), 900)
        self.assertIsNone(cl.known_clock_sinks(jobs[2:]))
        self.assertIsNone(cl.known_clock_sinks([dict(name="d", updated="x", textbook_lint={"lines": ["textbook_lint: PASS t"]})]))

    def test_cfg_reaches_the_in_flow_lint(self):
        j = dict(name="t", spec={"ref_tile": True}, clock_rule={"mode": "refuse", "evidence": GOOD, "closed_stands": False})
        self.assertEqual(cl.textbook_cfg(j)["clock"], {"enforce": True, "evidence": GOOD, "closed_stands": False})
        self.assertNotIn("clock", cl.textbook_cfg(dict(name="old", spec={"ref_tile": True})))   # in-flight job: untouched
        j["spec"]["textbook_lint"] = False                                          # lint off does not switch the rule off
        self.assertTrue(cl.textbook_cfg(j)["clock"]["enforce"])


def hjob(name, status, t, block="ot_t", reason=""):
    return dict(name=name, status=status, spec={"block": block}, finished_at=f"2026-10-12T{t}:00-07:00", reason=reason,
                events=[])


def new(name="t-v9-abcdef123", **kw):
    sp = {"name": name, "block": "ot_t", "stages": {"route": {"cmd": "x"}}}
    sp.update(kw)
    return dict(name=name, spec=sp, status="QUEUED", events=[])


class StructureRepeat(unittest.TestCase):
    def setUp(self):
        self.p = [patch.object(cl, "ledger", lambda *a, **k: None), patch.object(cl, "log", lambda *a, **k: None),
                  patch.object(cl, "STATE", Path(tempfile.mkdtemp()))]
        [p.start() for p in self.p]

    def tearDown(self):
        [p.stop() for p in self.p]

    def run_(self, hist, **kw):
        j = new(**kw)
        cl.structure_repeat_at_submit(j, hist)
        return j

    def test_two_failures_refuse(self):
        j = self.run_([hjob("a", "NEEDS_RTL", "01:00"), hjob("b", "EARLY_FAIL_SETUP", "02:00")])
        self.assertEqual(j["status"], "REFUSED")
        self.assertIn("STRUCTURE_REPEAT", j["reason"])
        self.assertIn("structural_change", j["reason"])

    def test_structural_change_admits_and_is_logged(self):
        j = self.run_([hjob("a", "NEEDS_RTL", "01:00"), hjob("b", "EARLY_FAIL_HOLD", "02:00")],
                      structural_change="split the tile into four hardened leaves with their own clock roots")
        self.assertEqual(j["status"], "QUEUED")
        self.assertEqual(j["submit_checks"]["structure_repeat"]["verdict"], "PASS")
        self.assertTrue(any("structural_change" in e for e in map(str, j["events"])))
        for bad in ("", "   ", "x", True, None):
            self.assertEqual(self.run_([hjob("a", "NEEDS_RTL", "01:00"), hjob("b", "NEEDS_RTL", "02:00")],
                                       structural_change=bad)["status"], "REFUSED", bad)

    def test_one_failure_or_other_block_passes(self):
        self.assertEqual(self.run_([hjob("a", "NEEDS_RTL", "01:00")])["status"], "QUEUED")
        self.assertEqual(self.run_([hjob("a", "NEEDS_RTL", "01:00"),
                                    hjob("b", "NEEDS_RTL", "02:00", block="ot_other")])["status"], "QUEUED")

    def test_closed_resets_the_count(self):
        h = [hjob("a", "NEEDS_RTL", "01:00"), hjob("b", "EARLY_FAIL_DRC", "02:00"), hjob("c", "CLOSED", "03:00"),
             hjob("d", "NEEDS_RTL", "04:00")]
        self.assertEqual(self.run_(h)["status"], "QUEUED")
        self.assertEqual(self.run_(h + [hjob("e", "EARLY_FAIL_CONGESTION", "05:00")])["status"], "REFUSED")

    def test_which_failures_count(self):
        crash = "route crashed twice (rc=1 ok-check failed;; first error: x)"
        self.assertEqual(self.run_([hjob("a", "NEEDS_HUMAN", "01:00", reason=crash),
                                    hjob("b", "NEEDS_HUMAN", "02:00", reason=crash)])["status"], "REFUSED")
        for st, why in (("NEEDS_HUMAN", "calibrate synth_or_place: the CTS-only run failed"), ("CANCELLED", ""),
                        ("REFUSED", ""), ("FLOORPLAN_MARGIN", ""), ("NEEDS_BUDGET", ""),
                        ("NEEDS_HUMAN", "route crashed twice (LOST: stage wrapper gone without an rc)")):
            self.assertEqual(self.run_([hjob("a", "NEEDS_RTL", "01:00"), hjob("b", st, "02:00", reason=why)])["status"],
                             "QUEUED", (st, why))

    def test_hold_overlay_rerun_exempt(self):
        h = [hjob("a", "NEEDS_RTL", "01:00"), hjob("b", "EARLY_FAIL_HOLD", "02:00")]
        for n in ("t-v9-abcdef123-hs", "t-v9-abcdef123-hs-cx"):
            self.assertEqual(self.run_(h, name=n)["status"], "QUEUED", n)
        self.assertEqual(self.run_(h, name="t-hsel-abcdef123")["status"], "REFUSED")

    def test_no_route_stage_and_modes(self):
        h = [hjob("a", "NEEDS_RTL", "01:00"), hjob("b", "NEEDS_RTL", "02:00")]
        self.assertEqual(self.run_(h, stages={"bench": []})["status"], "QUEUED")
        (cl.STATE / "ref_gate.json").write_text(json.dumps({"structure_repeat": "warn"}))
        j = self.run_(h)
        self.assertEqual((j["status"], j["submit_checks"]["structure_repeat"]["verdict"]), ("QUEUED", "WARN"))


if __name__ == "__main__":
    unittest.main()


class MultiDomainClockEvidence(unittest.TestCase):
    def output(self, source="cks[0]", hi=250):
        rows = [{"source": "ck[0]", "clock": "core_clk", "tt": {"all": {"min": 100, "max": 120}}},
                {"source": source, "clock": "str_clk", "tt": {"all": {"min": 190, "max": hi}}}]
        return ("GATE_TB textbook_lint: INFO clock_roots max_root_sinks=17460 root=port:cks[0]\n"
                "GATE_CK tt insertion all 100..120 ps (spread 20)\n" +
                "\n".join("GATE_CK_DOMAIN " + json.dumps(r) for r in rows))

    def test_largest_root_uses_its_own_tree(self):
        r = PG.clock_record(self.output(), True)
        self.assertEqual(r["measured_clock"], "str_clk")
        self.assertEqual((r["tt_insertion_ps"], r["tt_spread_ps"]), (250, 60))
        self.assertEqual(r["verdict"], "PASS")

    def test_secondary_domain_cannot_borrow_primary_domain_exception(self):
        self.assertEqual(PG.clock_record(self.output(hi=301), True)["verdict"], "REFUSE")
        r = PG.clock_record(self.output(source="other"), True)
        self.assertIsNone(r["tt_insertion_ps"])
        self.assertEqual(r["verdict"], "REFUSE")
