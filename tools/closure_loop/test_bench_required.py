"""BENCH-REQUIRED (owner 2026-10-13): a closure candidate needs a behavioural positive bench + a mutant AT SUBMIT, by the
merge guard's own definition; lint alone is refused; benched_by runs a composition gate's bench + mutant."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("CL_STATE", tempfile.mkdtemp(prefix="benchreq_"))
import closure_loop as cl  # noqa: E402

LINT = {"name": "lint", "cmd": "verilator --lint-only x.sv", "expect": "pass"}
POS = {"name": "exact", "cmd": "bash bench.sh", "expect": "pass"}
MUT = {"name": "neg_stale", "cmd": "bash bench.sh --mut 1", "expect": "fail"}


def spec(benches, **kw):
    s = {"name": "t_ref-v1-abcdef123", "block": "ot_t", "owner": "claude", "ref_tile": True,
         "source": {"branch": "claude/t", "commit": "abcdef123"},
         "stages": {"bench": benches, "route": {"cmd": "bash tools/ref_tile/ref_route.sh physical/ref_tile/t/kit.env"},
                    "calibrate": {"enabled": False, "reason": "in-run"}},
         "verdict": {"corner_sta": "{RUN}/sta/*.json", "drc_metrics": "{RUN}/5_2_route.json"}}
    s.update(kw)
    return s


def job(sp, **kw):
    j = dict(name=sp["name"], spec=sp, status="QUEUED", events=[], benches={})
    j.update(kw)
    return j


def results(sp, ok=True):
    return {cl.bench_key(b["name"]): {"expect": b["expect"], "ok": ok, "rc": 0} for b in sp["stages"]["bench"]}


class BenchRequired(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        (self.t / "main_publish_owner.json").write_text(json.dumps(
            {"auto_merge_guarded": True, "auto_merge_external_bench_prefixes": ["bfh_compact"]}))
        for p in (patch.object(cl, "STATE", self.t), patch.object(cl, "ledger", lambda *a, **k: None),
                  patch.object(cl, "log", lambda *a, **k: None)):
            p.start()
            self.addCleanup(p.stop)

    def submit(self, sp, **kw):
        sp, err = cl.expand_benched_by(sp)
        self.assertIsNone(err)
        j = job(sp, **kw)
        cl.bench_gate_at_submit(j)
        return j

    def test_lint_only_refused(self):
        j = self.submit(spec([LINT], no_bench_reason="tile alone has no golden"))
        self.assertEqual(j["status"], "REFUSED")
        self.assertIn("BENCH_REQUIRED", j["reason"])
        self.assertIn("no behavioral positive bench", j["reason"])

    def test_lint_plus_mutant_refused(self):
        self.assertEqual(self.submit(spec([LINT, MUT]))["status"], "REFUSED")

    def test_positive_without_mutant_refused(self):
        j = self.submit(spec([LINT, POS], no_bench_reason="x"))
        self.assertEqual(j["status"], "REFUSED")
        self.assertIn("no negative bench", j["reason"])

    def test_bench_plus_mutant_accepted(self):
        j = self.submit(spec([LINT, POS, MUT]))
        self.assertEqual(j["status"], "QUEUED")
        self.assertNotIn("bench_gate", j.get("submit_checks", {}))

    def test_benched_by_accepted_and_runs_the_gate(self):
        for gate in cl.composition_gates():
            sp = spec([LINT], benched_by=gate)
            self.assertEqual(cl.validate(sp), [], gate)
            j = self.submit(sp)
            self.assertEqual(j["status"], "QUEUED", gate)
            names = [b["name"] for b in j["spec"]["stages"]["bench"]]
            self.assertTrue(set(cl.gate_bench_names(gate)) <= set(names))
            keys = [s["key"] for s in cl.stage_list(j["spec"]) if s["kind"] == "bench"]
            # every gate bench becomes a stage, whatever the gate names them (exact / mutant / mutants / wire_mutant ...):
            # at least one positive and one negative among them (composition_gates.json is the source, not this test)
            gb = (cl.composition_gates()[gate].get("benches") or [])
            for x in gb:
                self.assertIn(cl.bench_key(f"{gate}_{x['name']}"), keys, gate)
            self.assertTrue(any(x.get("expect") == "pass" for x in gb) and any(x.get("expect") == "fail" for x in gb), gate)
            self.assertEqual(sp["stages"]["bench"], [LINT])        # the submitted spec is not modified
        self.assertGreaterEqual(len(cl.composition_gates()), 3)

    def test_unknown_gate_invalid(self):
        sp = spec([LINT], benched_by="no_such_gate")
        self.assertTrue(any("not a composition gate" in e for e in cl.validate(sp)))
        self.assertIsNotNone(cl.expand_benched_by(sp)[1])

    def test_registry_gates_hold_the_evidence(self):
        for gate, g in cl.composition_gates().items():
            ex = {cl.bench_key(f"{gate}_{b['name']}"): b["expect"] for b in g["benches"]}
            self.assertIsNone(cl.bench_evidence_gap(ex), gate)
            for b in g["benches"]:
                self.assertTrue(b.get("pass_regex") if b["expect"] == "pass" else b.get("fail_regex"), (gate, b["name"]))

    def test_non_candidate_not_refused(self):
        self.assertEqual(self.submit(spec([LINT], no_bench_reason="x", hold_merge="physical probe"))["status"], "QUEUED")

    def test_other_jobs_warn(self):
        j = self.submit(spec([LINT], no_bench_reason="re-route", ref_tile=False))
        self.assertEqual(j["status"], "QUEUED")
        self.assertEqual(j["submit_checks"]["bench_gate"]["verdict"], "WARN")

    def test_external_bench_waiver_matches_guard(self):
        sp = spec([], no_bench_reason="BF of record", name="bfh_compact-x-abcdef123")
        self.assertIsNone(cl.bench_gate_check(sp, sp["name"]))
        self.assertEqual(cl.bench_gate_check(spec([], no_bench_reason="x")), "no loop benches")

    def test_not_retroactive(self):
        # an existing QUEUED/RUNNING job is never re-judged (ingest skips known names); its successor only warns
        (self.t / "jobs").mkdir()
        (self.t / "jobs" / "old.json").write_text(json.dumps(job(spec([LINT], name="old"), status="RUNNING")))
        j = self.submit(spec([LINT], no_bench_reason="x", auto_react_parent="old"))
        self.assertEqual(j["status"], "QUEUED")
        self.assertTrue(j["bench_gate_grandfathered"])
        (self.t / "jobs" / "new.json").write_text(json.dumps(job(
            spec([LINT, POS, MUT], name="new"), submit_checks={"bench_gate": {"verdict": "PASS"}})))
        j = self.submit(spec([LINT], no_bench_reason="x", auto_react_parent="new"))
        self.assertEqual(j["status"], "REFUSED")

    def test_ingest_wiring(self):
        (self.t / "jobs").mkdir()
        gate = sorted(cl.composition_gates())[0]
        srcs = [("drop:a", spec([LINT], no_bench_reason="x", name="lintonly-a")),
                ("drop:b", spec([LINT], benched_by=gate, name="benched-b")),
                ("drop:c", spec([LINT, POS, MUT], name="full-c")),
                ("drop:d", spec([LINT], no_bench_reason="x", name="live-d"))]
        # live-d was ingested before the gate and is RUNNING: never re-judged
        (self.t / "jobs" / "live-d.json").write_text(json.dumps(job(srcs[3][1], status="RUNNING")))
        saved = {}
        noop = lambda *a, **k: None  # noqa: E731
        with patch.object(cl, "gfetch", noop), patch.object(cl, "route_keys", lambda: {}), \
                patch.object(cl, "load_sources", lambda: srcs), patch.object(cl, "lint_at_submit", noop), \
                patch.object(cl, "hier_lint_at_submit", noop), patch.object(cl, "ref_gate_at_submit", noop), \
                patch.object(cl, "bench_paths_at_submit", noop), \
                patch.object(cl, "save_job", lambda j: saved.__setitem__(j["name"], j)):
            cl.ingest()
        self.assertEqual(saved["lintonly-a"]["status"], "REFUSED")
        self.assertEqual(saved["full-c"]["status"], "QUEUED")
        b = saved["benched-b"]
        self.assertEqual(b["status"], "QUEUED")
        self.assertEqual(b["spec_submitted"], srcs[1][1])
        got = [x["name"] for x in b["spec"]["stages"]["bench"]]
        self.assertTrue(set(cl.gate_bench_names(gate)) <= set(got))
        neg = [x["name"] for x in cl.composition_gates()[gate]["benches"] if x.get("expect") == "fail"]
        self.assertTrue(neg and all(f"{gate}_{n}" in got for n in neg))
        self.assertNotIn("live-d", saved)

    def test_submit_and_guard_agree(self):
        """whatever the submit gate admits as a candidate, the guard accepts once its benches end as expected, and
        whatever the submit gate refuses the guard skips"""
        gate = sorted(cl.composition_gates())[0]
        for benches, kw in (([LINT], {"no_bench_reason": "x"}), ([LINT, MUT], {}), ([LINT, POS], {"no_bench_reason": "x"}),
                            ([LINT, POS, MUT], {}), ([LINT], {"benched_by": gate}), ([POS, MUT], {})):
            sp, _ = cl.expand_benched_by(spec(benches, **kw))
            why = cl.bench_gate_check(sp)
            guard = cl.auto_merge_guard(job(sp, benches=results(sp), commit_full="a" * 40))
            self.assertEqual(why, guard, (benches, kw))

    def test_guard_not_weakened(self):
        gate = sorted(cl.composition_gates())[0]
        sp, _ = cl.expand_benched_by(spec([LINT], benched_by=gate))
        full = results(sp)
        self.assertIsNone(cl.auto_merge_guard(job(sp, benches=full, commit_full="a" * 40)))
        # a benched_by job whose gate benches did not run stays unmerged, even with another behavioural pair
        other = {k: v for k, v in results(spec([LINT, POS, MUT])).items()}
        self.assertIn("composition gate benches did not run",
                      cl.auto_merge_guard(job(sp, benches=other, commit_full="a" * 40)))
        self.assertIn("benches not as expected", cl.auto_merge_guard(job(sp, benches=results(sp, ok=False), commit_full="a" * 40)))
        lint_only = spec([LINT], no_bench_reason="x")
        self.assertEqual(cl.auto_merge_guard(job(lint_only, benches=results(lint_only), commit_full="a" * 40)),
                         "no behavioral positive bench (lint alone is not exactness)")


if __name__ == "__main__":
    unittest.main()
