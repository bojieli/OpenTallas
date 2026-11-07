"""Execute the HBM runner's actual hold-margin block with GNU Make fixtures."""
import ast
import functools
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "physical/die_plan/hbm_arch_cores/run_kit_hbm.sh"


@functools.lru_cache(None)
def runtime_block(template):
    if template == "hbm":
        source = RUNNER.read_text()
    else:
        path = ROOT / "tools/die_plan" / ("core_flow.py" if template == "core" else "gen_phys.py")
        tree = ast.parse(path.read_text())
        assignments = {node.targets[0].id: node.value for node in tree.body
                       if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)}
        if template == "core":
            assert any(isinstance(n, ast.Name) and n.id == "HOLD_MARGIN_READ"
                       for n in ast.walk(assignments["FF_GRT_STEP"]))
            source = ast.literal_eval(assignments["HOLD_MARGIN_READ"])
        else:
            source = ast.literal_eval(assignments["RUN_KIT"])
    if template != "core":
        start = source.index("  HM=; if [")
        end = source.index('  if [ \\$rc = 0 ] && [ -n \\"\\$HM\\" ]', start)
        source = source[start:end]
    # Let Bash decode the existing outer Docker command quoting.
    return subprocess.check_output(["bash", "-c", "printf '%s' \"" + source + "\""], text=True)


@unittest.skipUnless(shutil.which("make"), "GNU Make required")
class HoldMarginCases:
    def evaluate(self, config, *, command_line="", prior_rc=0):
        with tempfile.TemporaryDirectory() as td:
            work = Path(td)
            (work / "config.mk").write_text(config + "\n")
            (work / "print.mk").write_text("print-%:\n\t@printf '%s: %s\\n' '$*' '$($*)'\n")
            block = runtime_block(self.TEMPLATE).replace("/work/", td + "/")
            script = (f'M="make --no-print-directory -s -f {work}/config.mk -f {work}/print.mk {command_line}"\n'
                      f"rc={prior_rc}\n" + block + '\nprintf "\\nHM_RESULT=%s\\n" "$HM"\nexit "$rc"\n')
            env = dict(os.environ)
            env.pop("OT_HOLD_FF_MARGIN", None)
            result = subprocess.run(["bash", "-c", script], text=True, capture_output=True, env=env)
            return result, (work / "FAIL_POSTCTS").read_text() if (work / "FAIL_POSTCTS").exists() else ""

    def test_actual_make_assignment_forms(self):
        cases = [
            ("export OT_HOLD_FF_MARGIN = 10", "10"),
            ("override export OT_HOLD_FF_MARGIN = 15", "15"),
            ("  override export OT_HOLD_FF_MARGIN := 15.5 # ps", "15.5 "),
            ("OT_HOLD_FF_MARGIN ?= 12\nOT_HOLD_FF_MARGIN ?= 13", "12"),
            ("BASE = 10\nexport OT_HOLD_FF_MARGIN = $(BASE)", "10"),
            ("override export OT_HOLD_FF_MARGIN = \\\n  15", "15"),
            ("export OT_HOLD_FF_MARGIN = .015", ".015"),
            ("export OT_HOLD_FF_MARGIN = 1e1", "1e1"),
            ("export OT_HOLD_FF_MARGIN = 0", "0"),
            ("export OT_HOLD_FF_MARGIN = -1", "-1"),
        ]
        for config, expected in cases:
            with self.subTest(config=config):
                result, fail = self.evaluate(config)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("HM_RESULT=" + expected + "\n", result.stdout)
                self.assertFalse(fail)

    def test_make_override_precedence(self):
        result, _ = self.evaluate("override export OT_HOLD_FF_MARGIN = 15\nOT_HOLD_FF_MARGIN = 20",
                                  command_line="OT_HOLD_FF_MARGIN=90")
        self.assertEqual(result.returncode, 0)
        self.assertIn("HM_RESULT=15\n", result.stdout)
        result, _ = self.evaluate("export OT_HOLD_FF_MARGIN = 15", command_line="OT_HOLD_FF_MARGIN=90")
        self.assertEqual(result.returncode, 0)
        self.assertIn("HM_RESULT=90\n", result.stdout)

    def test_unset_preserves_absent_margin(self):
        result, fail = self.evaluate("# no requested repair margin")
        self.assertEqual(result.returncode, 0)
        self.assertIn("HM_RESULT=\n", result.stdout)
        self.assertFalse(fail)

    def test_invalid_values_fail_before_repair(self):
        for value in ("NaN", "Inf", "1e9999", "10 20", "1_0", "bad"):
            with self.subTest(value=value):
                result, fail = self.evaluate("override export OT_HOLD_FF_MARGIN = " + value)
                self.assertEqual(result.returncode, 9, result.stdout + result.stderr)
                self.assertIn("invalid OT_HOLD_FF_MARGIN", fail)

    def test_make_failure_is_not_treated_as_absent(self):
        result, fail = self.evaluate("not valid Make syntax")
        self.assertEqual(result.returncode, 9)
        self.assertIn("hold margin Make read", fail)

    def test_existing_failure_is_preserved(self):
        result, fail = self.evaluate("not valid Make syntax", prior_rc=3)
        self.assertEqual(result.returncode, 3)
        self.assertFalse(fail)

    def test_old_reader_misses_the_reported_override(self):
        config = "override export OT_HOLD_FF_MARGIN = 15\n"
        old = subprocess.run(["sed", "-n", "s/^export OT_HOLD_FF_MARGIN = //p"],
                             input=config, text=True, capture_output=True, check=True)
        self.assertEqual(old.stdout, "")
        current, _ = self.evaluate(config)
        self.assertEqual(current.returncode, 0)
        self.assertIn("HM_RESULT=15\n", current.stdout)


class TestHBM(HoldMarginCases, unittest.TestCase):
    TEMPLATE = "hbm"


class TestCore(HoldMarginCases, unittest.TestCase):
    TEMPLATE = "core"


class TestPartition(HoldMarginCases, unittest.TestCase):
    TEMPLATE = "gen"


if __name__ == "__main__":
    unittest.main()
