"""Receipt integrity tests; simulation is stubbed, no arithmetic qualification."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

GATE = Path(__file__).resolve().parents[1] / "cp_gate.py"


class SourceBindingTest(unittest.TestCase):
    def run_gate(self, mutation=None, missing_fixtures=False):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            paths = ["rtl/dsrom_sys/s81_suhc/ot_s81_su_cp.sv",
                     "rtl/dsrom_sys/s81_suhc/ot_s81_su_cp_vm.sv",
                     "rtl/dsrom_sys/s81_suhc/test/tb_s81_su_cp_vm.sv",
                     "physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v"]
            for name in paths:
                p = root / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("source before build")
            fixtures = root / "fixtures"
            fixtures.mkdir()
            if not missing_fixtures:
                (fixtures / "L02").mkdir()
                (fixtures / "L02/data.mem").write_text("0000")
            work = root / "work"
            receipt = work / "build_vm_m0/receipt.json"
            receipt.parent.mkdir(parents=True)
            receipt.write_text('{"verdict":"PASS","stale":true}')
            gate_module = types.ModuleType("su_gate")
            gate_module.RTL = []
            gate_module.H = types.SimpleNamespace(FP={"rtl": []})

            def simulate(cmd, **kwargs):
                if "--binary" in cmd:
                    if mutation == "source":
                        (root / paths[0]).write_text("mutated source")
                    if mutation == "fixture":
                        (fixtures / "L02/data.mem").write_text("FFFF")
                    if mutation == "added_fixture":
                        (fixtures / "L02/new.mem").write_text("FFFF")
                    if mutation == "build_failure":
                        return subprocess.CompletedProcess(cmd, 1)
                    return subprocess.CompletedProcess(cmd, 0)
                if "+LATE=1" in cmd:
                    return subprocess.CompletedProcess(cmd, 1,
                        "CP_VM FAIL cycles139 scheduled139 fault1 cycles272 scheduled272 fault1", "")
                return subprocess.CompletedProcess(cmd, 0, "CP_VM PASS", "")

            argv = [str(GATE), "--work", str(work), "--fixtures", str(fixtures)]
            outcome = None
            oldpath = sys.path[:]
            try:
                with patch.dict(sys.modules, {"su_gate": gate_module}), patch.object(sys, "argv", argv), patch("subprocess.run", simulate):
                    try:
                        exec(compile(GATE.read_text(), str(GATE), "exec"),
                             {"__file__": str(root / "tools/s81_ftok/cp_gate.py"), "__name__": "__main__"})
                    except (RuntimeError, SystemExit) as exc:
                        outcome = exc
            finally:
                sys.path[:] = oldpath
            return outcome, json.loads(receipt.read_text()) if receipt.exists() else None

    def test_unchanged_inputs_emit_bound_receipt(self):
        outcome, receipt = self.run_gate()
        self.assertIsInstance(outcome, SystemExit)
        self.assertEqual(outcome.code, 0)
        self.assertEqual(receipt["verdict"], "PASS")
        self.assertEqual(len(receipt["source_sha256"]), 4)
        self.assertEqual(len(receipt["fixture_sha256"]), 1)
        self.assertNotIn("stale", receipt)

    def test_changed_source_or_fixture_cannot_issue_receipt(self):
        for mutation in ("source", "fixture", "added_fixture"):
            with self.subTest(mutation=mutation):
                outcome, receipt = self.run_gate(mutation)
                self.assertIsInstance(outcome, RuntimeError)
                self.assertIn("changed during build/run", str(outcome))
                self.assertIsNone(receipt)

    def test_build_failure_removes_stale_receipt(self):
        outcome, receipt = self.run_gate("build_failure")
        self.assertEqual(outcome.code, 1)
        self.assertIsNone(receipt)

    def test_empty_fixtures_refused(self):
        outcome, receipt = self.run_gate(missing_fixtures=True)
        self.assertIsInstance(outcome, RuntimeError)
        self.assertIn("no CP fixtures", str(outcome))
        self.assertIsNone(receipt)


if __name__ == "__main__":
    unittest.main()
