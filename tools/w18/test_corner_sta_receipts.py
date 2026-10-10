"""Receipt regressions: a failed STA process must never look like clean timing."""
import pathlib
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import corner_sta as C


class CornerReceiptTests(unittest.TestCase):
    def run_fixture(self, stdout, stderr="", rc=0):
        with tempfile.TemporaryDirectory() as tmp:
            orfs = pathlib.Path(tmp)
            base = orfs / "results/asap7/fixture/base"
            base.mkdir(parents=True)
            for name in ("6_final.odb", "6_final.spef"):
                (base / name).write_bytes(b"")
            (base / "6_final.sdc").write_text("create_clock -name serial -period 1111.111 [get_ports clk]\n")
            process = subprocess.CompletedProcess([], rc, stdout, stderr)
            with patch.object(C.subprocess, "run", return_value=process):
                result = C.run(orfs, "tt", [])
            return result, (orfs / "w18_sta_tt.log").read_text()

    def test_success_preserves_seconds_to_ps_and_negative_slack(self):
        result, _ = self.run_fixture("OT_WS -7.5e-13\nOT_TNS -1.25e-12\n")
        self.assertEqual(result["worst_slack_ps"], -0.75)
        self.assertEqual(result["tns_ps"], -1.2)
        self.assertEqual(result["errors"], [])

    def test_process_failure_preserves_stderr_and_is_not_clean(self):
        result, log = self.run_fixture("", "Error: cannot load routed database\n", 1)
        self.assertIn("cannot load routed database", log)
        self.assertEqual(result["tool_rc"], 1)
        self.assertIsNone(result["worst_slack_ps"])
        self.assertTrue(result["errors"])

    def test_tcl_error_cannot_pass_with_partial_positive_metrics(self):
        result, _ = self.run_fixture("OT_WS 1.0e-10\nOT_TNS 0\n", "Error: invalid propagated clock\n")
        self.assertIsNone(result["worst_slack_ps"])
        self.assertFalse(C.timing_checks_pass({"setup_tt": result, "hold_ff": result}))

    def test_missing_or_nonfinite_worst_slack_is_a_receipt_error(self):
        for value in ("", "OT_WS nan\n", "OT_WS INF\n", "OT_WS malformed\n"):
            with self.subTest(value=value):
                result, _ = self.run_fixture(value)
                self.assertIsNone(result["worst_slack_ps"])
                self.assertTrue(result["errors"])

    def test_thresholds_and_tool_validity_both_gate_timing(self):
        good = {"worst_slack_ps": 0.0, "tool_rc": 0, "errors": []}
        self.assertTrue(C.timing_checks_pass({"setup_tt": good, "hold_ff": good}))
        for bad in ({**good, "worst_slack_ps": -0.01}, {**good, "tool_rc": 1},
                    {**good, "errors": ["Error: invalid clock"]}):
            with self.subTest(bad=bad):
                self.assertFalse(C.timing_checks_pass({"setup_tt": good, "hold_ff": bad}))


if __name__ == "__main__":
    unittest.main()
