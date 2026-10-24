"""RULE ENFORCEMENT (owner 2026-10-13, el1013-rule-enforcement).
1. Clock rule (OWNER DECISION 2026-10-23, supersedes the 10-17 0dq spread FAIL): FAIL only on a measured related
   launch/capture flop-pair skew with CPPR > 80 ps at TT or FF ("<c>_pair_skew_ps"); spreads are information only (a
   measured record without pair skew WARNs); > 15,000 sinks on one root or insertion > 300 ps is a WARN; a declared
   spine or a spec waiver does not waive a pair-skew FAIL; CLOSED tiles stand.  pre_route_gate.clock_record does not
   carry pair skew yet, so its spread-only records are WARN, never REFUSE.
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
GOODP = dict(GOOD, tt_pair_skew_ps=60.0, ff_pair_skew_ps=50.0)


def lint_res(n):
    return {"findings": {}, "refuse": {}, "metrics": {"clock_max_root_sinks": n, "clock_max_root": "port:ck"}}


def gate_out(n, lo=None, hi=None, ff=(90.0, 120.0)):
    s = f"GATE_TB textbook_lint: INFO clock_roots max_root_sinks={n} root=port:ck rule=FAIL: x\nGATE_CTS_RC=0\n"
    if hi is not None:
        s += (f"GATE_CK ss insertion all 300.0..420.0 ps (spread 120.0), boundary mean 350; tt insertion all "
              f"{lo}..{hi} ps (spread {round(hi - lo, 1)}), boundary mean 200; ff insertion all {ff[0]}..{ff[1]} ps "
              f"(spread {round(ff[1] - ff[0], 1)}), boundary mean 100; macro_clk flag None\n")
    return s


class ClockRule(unittest.TestCase):
    def test_constants_are_the_owner_numbers(self):
        self.assertEqual((TL.CLK_ROOT_SINKS_MAX, TL.CLK_INSERTION_MAX_PS, TL.CLK_PAIR_SKEW_MAX_PS), (15000, 300.0, 80.0))

    def test_rule(self):
        E = TL.clock_rule_eval
        self.assertEqual(E(15000)[0], "PASS")
        self.assertEqual(E(15001)[0], "WARN")                                       # sinks alone: guidance
        self.assertTrue(TL.clock_rule(15001)[0])
        self.assertEqual(E(48000, GOODP)[0], "WARN")
        self.assertEqual(E(9000, dict(GOODP, max_root_sinks=9000))[0], "PASS")
        self.assertEqual(E(48000, dict(GOODP, tt_insertion_ps=900.0))[0], "WARN")   # insertion alone: guidance
        self.assertEqual(E(9000, dict(GOODP, tt_pair_skew_ps=80.0))[0], "PASS")
        self.assertEqual(E(9000, dict(GOODP, tt_pair_skew_ps=80.1))[0], "FAIL")
        self.assertFalse(TL.clock_rule(9000, dict(GOODP, tt_pair_skew_ps=80.1))[0])
        self.assertEqual(E(9000, dict(GOODP, ff_pair_skew_ps=80.1))[0], "FAIL")     # FF pair skew counts too
        # spread is information only (owner 10-23): over 80 with pair skew in limit passes, and is still printed
        r = E(9000, dict(GOODP, tt_spread_ps=140.0, ff_pin_spread_ps=95.0))
        self.assertEqual(r[0], "PASS")
        self.assertIn("FF pin-flop spread 95.0 ps (info)", r[1])
        r = E(9000, dict(GOOD, ff_pin_spread_ps=95.0))                              # spread only: WARN, not FAIL
        self.assertEqual(r[0], "WARN")
        self.assertIn("pair skew not measured", r[1])
        self.assertIn("FF pair skew not measured", E(9000, dict(GOOD, tt_pair_skew_ps=50.0))[1])
        self.assertIn("FF spread not measured", E(9000, GOOD)[1])
        self.assertEqual(E(48000, dict(GOOD, tt_spread_ps=None))[0], "WARN")         # no spread measured
        self.assertIn("not this netlist", E(48000, dict(GOOD, max_root_sinks=20000))[1])
        self.assertIn("250.0 ps", TL.clock_rule(48000, GOOD)[1])
        self.assertIn("60.0 ps", TL.clock_rule(100, GOODP)[1])                      # measured numbers always reported

    def test_lint_refuses_pair_skew_in_every_mode_and_ignores_waivers(self):
        bad = dict(GOODP, ff_pair_skew_ps=95.0)
        for mode in ("warn", "refuse"):
            r = TL.verdict(lint_res(48000), mode, waive=("clock_sinks", "clock_domain"), refuse_checks=(),
                           clock={"enforce": True, "evidence": bad})
            self.assertEqual((r["verdict"], r["refusing_checks"]), ("REFUSE", ["clock_sinks"]), mode)
            self.assertIn("FF pair skew 95.0 ps > 80", r["refuse"]["clock_sinks"][0])
            r = TL.verdict(lint_res(48000), mode, refuse_checks=(), clock={"enforce": True,
                                                                           "evidence": dict(GOOD, ff_pin_spread_ps=95.0)})
            self.assertEqual(r["refusing_checks"], [], mode)                       # spread alone never refuses
            r = TL.verdict(lint_res(48000), mode, refuse_checks=(), clock={"enforce": True})
            self.assertEqual((r["verdict"], r["refusing_checks"]), ("WARN", []), mode)   # sinks alone: WARN
            self.assertIn("clock_guidance", r["findings"])

    def test_lint_evidence_closed_and_small(self):
        self.assertEqual(TL.verdict(lint_res(48000), "refuse", clock={"enforce": True, "evidence": GOOD})["verdict"], "WARN")
        ins = dict(GOOD, tt_insertion_ps=410.0)
        self.assertEqual(TL.verdict(lint_res(48000), "refuse", clock={"enforce": True, "evidence": ins})["verdict"], "WARN")
        bad = dict(GOOD, tt_pair_skew_ps=95.0)
        self.assertEqual(TL.verdict(lint_res(48000), "refuse", clock={"enforce": True, "evidence": bad})["verdict"], "REFUSE")
        r = TL.verdict(lint_res(48000), "refuse", clock={"enforce": True, "evidence": bad, "closed_stands": True})
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
        self.assertEqual(it["severity"], "WARN")                                   # no pair skew in the gate record yet
        self.assertIn("pair skew not measured", it["message"])
        self.assertIn("TT insertion 190.0 ps", it["message"])
        self.assertIn("TT leaf spread 40.0 ps", it["message"])
        self.assertIn("FF leaf spread 30.0 ps", it["message"])                       # the FF spread report
        self.assertEqual((g.clock["ff_insertion_ps"], g.clock["ff_spread_ps"]), (120.0, 30.0))

    def test_ff_spread_reported_not_failed(self):
        g, it = self.item(gate_out(9000, 150.0, 190.0, ff=(60.0, 150.0)), True)
        self.assertEqual(it["severity"], "WARN")                                   # owner 10-23: spread is information
        self.assertIn("FF leaf spread 90.0 ps (info)", it["message"])

    def test_big_root_without_cts_warns(self):
        g, it = self.item(gate_out(48000), False)
        self.assertEqual(it["severity"], "WARN")
        self.assertIn("guidance", it["message"])

    def test_declared_spine_spread_is_not_a_fail(self):
        g, it = self.item(gate_out(48000, 190.0, 290.0), True, {"clock": "spine"})
        self.assertEqual(it["severity"], "WARN")                                   # 100 ps spread: information only

    def test_big_root_never_fails_on_spread(self):
        g, it = self.item(gate_out(48000, 210.0, 280.0), True, {"clock": "spine"})
        self.assertEqual(it["severity"], "WARN")
        self.assertEqual((g.clock["tt_insertion_ps"], g.clock["tt_spread_ps"], g.clock["verdict"]), (280.0, 70.0, "WARN"))
        g, it = self.item(gate_out(9000, 250.0, 320.0), True)               # insertion > 300 alone: WARN
        self.assertEqual(it["severity"], "WARN")
        g, it = self.item(gate_out(48000, 190.0, 290.0), True)              # spread miss: information only
        self.assertEqual(it["severity"], "WARN")

    def kit(self, td, clock=None, hold_context=True):
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
            if hold_context:        # every current gate records the route hold context (gate_route_hold_context)
                binding["route_hold_context"] = {"fixture": True}
            (kd / PG.CLOCK_RESULT).write_text(json.dumps({"clock": clock, "source_binding": binding}))
        return kd

    def test_submit_side(self):
        with tempfile.TemporaryDirectory() as td, patch.object(PG, "ROOT", None):
            PG.ROOT = Path(td)
            sev = lambda kd, **kw: (lambda g: (PG.check_clock_evidence(g, kd, **kw), g.verdict)[1])(PG.Gate())  # noqa: E731
            self.assertEqual(sev(self.kit(td)), "PASS")                            # nothing known: in-flow lint judges
            self.assertEqual(sev(self.kit(td), known_sinks=48000), "WARN")         # history says big: guidance
            self.assertEqual(sev(self.kit(td), known_sinks=48000, closed_stands=True), "PASS")
            self.assertEqual(sev(self.kit(td), known_sinks=9000), "PASS")
            self.assertEqual(sev(self.kit(td, GOOD), known_sinks=48000), "WARN")   # measured, sinks > 15k: guidance
            good9 = dict(GOODP, max_root_sinks=9000, ff_spread_ps=50.0)
            self.assertEqual(sev(self.kit(td, good9), known_sinks=48000), "PASS")
            self.assertEqual(sev(self.kit(td, GOOD, hold_context=False), known_sinks=48000), "WARN")  # historical gate
            self.assertEqual(sev(self.kit(td, dict(GOOD, tt_spread_ps=95.0))), "WARN")        # spread: information
            self.assertEqual(sev(self.kit(td, dict(GOODP, tt_pair_skew_ps=95.0))), "FAIL")
            self.assertEqual(sev(self.kit(td, dict(GOODP, ff_pair_skew_ps=81.0))), "FAIL")
            self.assertEqual(sev(self.kit(td, dict(GOOD, tt_insertion_ps=None, tt_spread_ps=None))), "WARN")
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

    def serial_bench_failure(self):
        j = hjob("serial", "NEEDS_RTL", "02:00", reason="bench_exact expected PASS but rc=0")
        j.update(attempt=1, retries_used=0, bench_par=False, stage_idx=0,
                 stage_key="bench_exact", stage_tag="bench_exact.a1",
                 benches={"bench_exact": {"expect": "pass", "rc": 0, "ok": False}},
                 events=["2026-10-12T01:00 ingested from fixture.json",
                         "2026-10-12T01:01 launched bench_exact (attempt 1) on ot-epyc4",
                         "2026-10-12T01:02 NEEDS_RTL: bench_exact expected PASS but rc=0"])
        j["spec"].update(bench_first=True, stages={"bench": [{"name": "exact"}], "route": {"cmd": "route"}})
        return j

    def test_proved_serial_bench_failure_does_not_count_as_route(self):
        j = self.serial_bench_failure()
        self.assertFalse(cl.terminal_route_failure(j))
        self.assertEqual(self.run_([hjob("physical", "NEEDS_RTL", "01:00"), j])["status"], "QUEUED")

    def test_ambiguous_or_physical_bench_failure_still_counts(self):
        import copy
        base = self.serial_bench_failure()
        variants = []
        for key in ("bench_par", "attempt", "retries_used", "stage_idx", "stage_key", "stage_tag", "benches", "events"):
            j = copy.deepcopy(base)
            j.pop(key)
            variants.append(("missing " + key, j))
        for changes in ({"bench_par": True}, {"attempt": 2}, {"retries_used": 1},
                        {"stage_key": "route", "stage_tag": "route.a1"},
                        {"ctrack": {"state": "done"}}, {"metrics": {"tt": -1}},
                        {"crashes": [{"stage": "route"}]}, {"status": "EARLY_FAIL_SETUP"}):
            j = copy.deepcopy(base)
            j.update(changes)
            variants.append((str(changes), j))
        j = copy.deepcopy(base)
        j["events"].insert(1, "2026-10-12T01:00 launched route (attempt 1) on ot-epyc4")
        variants.append(("mixed route/bench", j))
        j = copy.deepcopy(base)
        j["events"] = j["events"][1:]
        variants.append(("truncated history", j))
        j = copy.deepcopy(base)
        j["benches"]["bench_exact"]["track"] = "parallel"
        variants.append(("parallel receipt", j))
        for why, j in variants:
            with self.subTest(why=why):
                self.assertTrue(cl.terminal_route_failure(j))

    def test_actual_parallel_bench_cancelled_routes_and_fail_closed_mutants(self):
        import copy
        fixtures = sorted((HERE / "testdata" / "bench_cancelled_routes").glob("*.json"))
        self.assertEqual(len(fixtures), 2)
        hist = [json.loads(p.read_text()) for p in fixtures]
        for j in hist:
            self.assertFalse(cl.terminal_route_failure(j))
            for key in ("bench_par", "events", "textbook_seen", "btrack", "benches", "stage_tag"):
                bad = copy.deepcopy(j)
                bad.pop(key)
                self.assertTrue(cl.terminal_route_failure(bad), key)
            for field, value in (("metrics", {"tt_ps": -1}), ("early_fail", {"verdict": "EARLY_FAIL_HOLD"}),
                                 ("crashes", [{"stage": "route"}]), ("status", "EARLY_FAIL_SETUP")):
                bad = copy.deepcopy(j)
                bad[field] = value
                self.assertTrue(cl.terminal_route_failure(bad), field)
            for event in ("route crashed twice", "route done (rc=0)", "EARLY_FAIL_SETUP: failed",
                          "bench failed: could not stop route", "launched signoff (attempt 1) on ot-epyc4"):
                bad = copy.deepcopy(j)
                bad["events"].insert(-2, "2026-10-15T08:08:00-07:00 " + event)
                self.assertTrue(cl.terminal_route_failure(bad), event)
        # Actual delivery successor no longer needs a fabricated structural change.
        self.assertEqual(self.run_(hist, block=hist[0]["spec"]["block"])["status"], "QUEUED")

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
        self.assertEqual(r["verdict"], "WARN")                     # 17,460 sinks > 15k: guidance only

    def test_ff_pin_flop_spread_from_domain(self):
        rows = [{"source": "cks[0]", "clock": "str_clk", "tt": {"all": {"min": 190, "max": 250}, "boundary": {"min": 200, "max": 240}},
                 "ff": {"all": {"min": 100, "max": 150}, "boundary": {"min": 100, "max": 190}}}]
        out = ("GATE_TB textbook_lint: INFO clock_roots max_root_sinks=9000 root=port:cks[0]\n" +
               "\n".join("GATE_CK_DOMAIN " + json.dumps(r) for r in rows))
        r = PG.clock_record(out, True)
        self.assertEqual((r["tt_pin_spread_ps"], r["ff_spread_ps"], r["ff_pin_spread_ps"]), (40.0, 50.0, 90.0))
        self.assertEqual(r["verdict"], "WARN")                     # owner 10-23: 90 ps FF spread is information

    def test_secondary_domain_cannot_borrow_primary_domain_exception(self):
        self.assertEqual(PG.clock_record(self.output(hi=301), True)["verdict"], "WARN")   # spread: information
        r = PG.clock_record(self.output(source="other"), True)
        self.assertIsNone(r["tt_insertion_ps"])
        self.assertEqual(r["verdict"], "WARN")                     # no own measurement: guidance, not a borrowed PASS


class EveryRootJudged(unittest.TestCase):
    """KV-CLKFIX 10-19: a two-clock kit's second root is judged by the same pin-flop rule (not only the largest root)."""
    def out(self, h_tt=(230, 270), h_ff=(200, 230), boundary=True):
        dom = lambda lo, hi: dict({"all": {"n": 900, "min": lo - 10, "max": hi}}, **({"boundary": {"min": lo, "max": hi}} if boundary else {}))
        rows = [{"source": "ck", "clock": "core_clk", "tt": dom(200, 240), "ff": dom(160, 190)},
                {"source": "hck", "clock": "hclk", "tt": dom(*h_tt), "ff": dom(*h_ff)}]
        return ("GATE_TB textbook_lint: INFO clock_roots max_root_sinks=9000 root=port:ck\n" +
                "\n".join("GATE_CK_DOMAIN " + json.dumps(r) for r in rows))

    def test_second_root_within_limit_passes(self):
        r = PG.clock_record(self.out(), True)
        self.assertEqual(r["verdict"], "WARN")                     # no pair skew in the gate record: WARN
        self.assertEqual([(x["source"], x["tt_pin_spread_ps"], x["verdict"]) for x in r["other_roots"]], [("hck", 40.0, "WARN")])

    def test_second_root_over_limit_refuses(self):
        r = PG.clock_record(self.out(h_tt=(160, 290)), True)
        self.assertEqual(r["verdict"], "WARN")                     # owner 10-23: second-root spread is information
        self.assertEqual(r["other_roots"][0]["verdict"], "WARN")

    def test_root_without_pin_flops_not_judged(self):
        r = PG.clock_record(self.out(h_tt=(160, 290), boundary=False), True)
        self.assertEqual(r["verdict"], "WARN")
        self.assertEqual(r["other_roots"][0]["verdict"], "INFO")

    def test_without_cts_unchanged(self):
        self.assertNotIn("other_roots", PG.clock_record(self.out(h_tt=(160, 290)), False))


class EveryRootRequirement(unittest.TestCase):
    """KV-CLKFIX 10-19: Gate-Rule tightening requires=every_root_spread keeps older one-root / in-limit gates."""
    def test_scoping(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ref_tile"))
        import source_binding as SB
        dom = lambda s, c, lo, hi: {"source": s, "clock": c, "tt": {"boundary": {"min": lo, "max": hi}},
                                    "ff": {"boundary": {"min": lo, "max": hi}}}
        ok = lambda ck: SB.relaxed_rule_requirement(["every_root_spread"], ck)[0]
        self.assertTrue(ok({"clock_measurements": [dom("ck", "core_clk", 100, 300)]}))
        self.assertTrue(ok({"measured_clock": "core_clk", "clock_measurements": [dom("ck", "core_clk", 100, 300),
                                                                                  dom("hck", "hclk", 200, 260)]}))
        self.assertFalse(ok({"measured_clock": "core_clk", "clock_measurements": [dom("ck", "core_clk", 100, 150),
                                                                                   dom("hck", "hclk", 200, 300)]}))
        self.assertTrue(ok({}))


class EveryRootCornersAndChildren(unittest.TestCase):
    def test_second_root_ff_alone_can_refuse_and_exact_limit_passes(self):
        f = EveryRootJudged()
        r = PG.clock_record(f.out(h_tt=(200, 280), h_ff=(100, 181)), True)
        self.assertEqual(r["verdict"], "WARN")                     # owner 10-23: spread never refuses
        self.assertEqual(PG.clock_record(f.out(h_tt=(200, 280), h_ff=(100, 180)), True)["verdict"], "WARN")

    def test_nested_child_flop_boundary_requirement_uses_compensated_span(self):
        import source_binding as SB
        domains = [{"source":"ck", "clock":"core_clk"}, {"source":"hck", "clock":"hclk"}]
        for lo, hi, ok in ((200,280,True),(200,281,False)):
            domains[1]["tt"] = {"boundary":{"min":100,"max":120},
                                "child_flop":{"all":{"min":lo,"max":hi},
                                              "boundary":{"min":lo,"max":hi}}}
            clock = {"measured_clock":"core_clk", "clock_measurements":domains}
            self.assertEqual(SB.relaxed_rule_requirement(["every_root_spread"], clock)[0], ok)
