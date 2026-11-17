"""Reviewed inherited G0 findings retain exact identities and contexts; no count waiver."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import publish_gate as P


class Baseline(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.root = Path(self.td.name)
        self.plan = self.root / "plan.json"
        self.plan.write_text("{}")
        self.error = dict(level="ERROR", check="cuts", msg="horizontal 10500: 4464 bits on 6686 tracks = 0.67", part="s_0S_L0")
        self.base = dict(schema="opentallas.publish_gate.g0_baseline.v1",
                         reviewed_plan_sha256=P.sha256_file(self.plan),
                         reviewed_g0_sha256="a"*64, review="COORD reviewed C3 GO",
                         accepted_errors=[self.error])
        self.report = dict(schema="opentallas.die_plan.g0.v1", verdict="FAIL", errors=1, findings=[self.error])

    def check(self, report=None, base=None, rc=1):
        return P.g0_baseline_check(self.plan, self.report if report is None else report,
                                   self.base if base is None else base, rc)

    def test_exact_inherited_and_subset_pass(self):
        base = copy.deepcopy(self.base)
        base["accepted_errors"].append(dict(self.error, part="other"))
        self.assertEqual(self.check(base=base)["verdict"], "PASS")
        self.assertTrue(self.check()["inherited"])

    def test_equal_count_new_identity_or_context_fails(self):
        for field, value in (("msg", self.error["msg"]+" changed"), ("part", "s_0S_L1"), ("check", "geometry")):
            report = copy.deepcopy(self.report)
            report["findings"][0][field] = value
            self.assertEqual(self.check(report=report)["verdict"], "FAIL")

    def test_duplicate_excess_fails(self):
        report = dict(self.report, errors=2, findings=[self.error, self.error])
        self.assertEqual(self.check(report=report)["verdict"], "FAIL")

    def test_baseline_plan_identity_and_review_required(self):
        for key, value in (("reviewed_plan_sha256", "b"*64), ("reviewed_g0_sha256", ""), ("review", "")):
            self.assertEqual(self.check(base=dict(self.base, **{key:value}))["verdict"], "FAIL")

    def test_checker_crash_or_stale_report_never_waived(self):
        for rc in (2, 99):
            self.assertEqual(self.check(rc=rc)["verdict"], "FAIL")
        for report in ({}, dict(self.report, verdict="PASS"), dict(self.report, errors=0), dict(self.report, pending_view=1)):
            self.assertEqual(self.check(report=report)["verdict"], "FAIL")

    def test_default_zero_error_policy_unchanged(self):
        self.assertEqual(P.g0_baseline_check(self.plan, self.report, None, 1)["verdict"], "FAIL")
        self.assertEqual(P.g0_baseline_check(self.plan, None, None, 0)["verdict"], "PASS")

    def test_record_bytes_are_pinned(self):
        path = self.root / "baseline.json"
        path.write_text(json.dumps(self.base))
        spec = dict(path=str(path), sha256=P.sha256_file(path))
        self.assertEqual(P.load_g0_baseline(spec)["accepted_errors"], [self.error])
        path.write_text("{}")
        with self.assertRaisesRegex(ValueError, "path/hash mismatch"):
            P.load_g0_baseline(spec)

    def test_pre_failure_still_blocks_with_accepted_g0(self):
        def fake_sub(argv, cwd):
            if "--out" in argv:
                out = Path(argv[argv.index("--out")+1]);out.mkdir(exist_ok=True)
                (out/"g0_report.json").write_text(json.dumps(self.report))
                return 1, "G0 FAIL inherited"
            if "check" in argv:
                return 1, "PRE INPUT error"
            return 0, "SCHEMA PASS"
        with patch.object(P, "_sub", fake_sub), patch.object(P, "check_hashes", return_value=([],1)), patch.object(P, "check_contained", return_value=[]):
            out = P.run_static(self.root, self.plan, work=self.root/"work", g0_baseline=self.base)
        self.assertEqual(out["pre_g0"]["baseline"]["verdict"], "PASS")
        self.assertEqual(out["pre_g0"]["verdict"], "FAIL")
        self.assertEqual(out["pre_g0"]["pre_rc"], 1)


if __name__ == "__main__":
    unittest.main()
