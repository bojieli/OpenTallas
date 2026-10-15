"""Regression coverage for preserved hierarchy statistics; no synthesis required."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from run_abi3_physical import FlowError, parse_stat, scan_liberty, summarize_stat

DATA = Path(__file__).parent / "testdata" / "physical_stat"


class PhysicalStat(unittest.TestCase):
    def setUp(self):
        self.cells = json.loads((DATA / "library_cell_metadata.json").read_text())["cells"]
        self.raw = (DATA / "s81_ctl_phw10.txt").read_text()

    def test_actual_preserved_control(self):
        stat = parse_stat(self.raw, "ot_s81_pq_ctl_static_native")
        result = summarize_stat(stat, self.cells)
        self.assertEqual(result["cell_count"], 12930)
        self.assertEqual(result["cell_area_um2"], 1829.017260)
        self.assertEqual(result["sequential_cell_count"], 2936)
        self.assertEqual(result["macro_count"], 0)
        self.assertEqual(result["unmapped_cell_types"], [])
        self.assertEqual(result["stat_selection"]["basis"], "design hierarchy leaf cells")

    def test_actual_flat_reader(self):
        stat = parse_stat((DATA / "s81_flat_reader.txt").read_text(), "ot_s81_pq_calendar_reader")
        result = summarize_stat(stat, self.cells)
        self.assertEqual(result["cell_count"], 2492)
        self.assertEqual(result["cell_area_um2"], 374.793480)
        self.assertEqual(result["sequential_cell_count"], 595)
        self.assertEqual(result["macro_count"], 0)

    def test_wrong_top_rejected(self):
        with self.assertRaisesRegex(FlowError, "top mismatch"):
            parse_stat(self.raw, "other_top")

    def test_multiple_stat_invocations_rejected(self):
        with self.assertRaisesRegex(FlowError, "multiple design hierarchy"):
            parse_stat(self.raw + self.raw)

    def test_local_modules_without_hierarchy_rejected(self):
        with self.assertRaisesRegex(FlowError, "one flat module"):
            parse_stat(self.raw.split("=== design hierarchy ===")[0])

    def test_inconsistent_count_rejected(self):
        bad = self.raw.replace("12930 1.83E+03 cells", "12931 1.83E+03 cells")
        with self.assertRaisesRegex(FlowError, "cell table disagrees"):
            parse_stat(bad)

    def test_inconsistent_area_rejected(self):
        stat = parse_stat(self.raw.replace("1829.017260", "1900.017260"))
        with self.assertRaisesRegex(FlowError, "chip area disagrees"):
            summarize_stat(stat, self.cells)

    def test_unknown_cell_is_retained_and_not_a_macro(self):
        stat = parse_stat(self.raw)
        cells = copy.deepcopy(self.cells)
        del cells["DFFHQNx1_ASAP7_75t_R"]
        result = summarize_stat(stat, cells)
        self.assertEqual(result["unmapped_cell_count"], 2252)
        self.assertEqual(result["macro_count"], 0)
        self.assertEqual(result["cell_count"], 12930)
        self.assertEqual(result["unmapped_cell_types"], ["DFFHQNx1_ASAP7_75t_R"])
        self.assertEqual(result["sequential_cell_count"], 684)

    def test_unknown_area_remains_unknown(self):
        stat = parse_stat("=== top ===\n 1 - cells\n 1 - UNKNOWN\n", "top")
        result = summarize_stat(stat, {})
        self.assertIsNone(result["cell_area_um2"])
        self.assertEqual(result["unknown_area_cell_types"], ["UNKNOWN"])
        self.assertEqual(result["macro_count"], 0)

    def test_real_sram_liberty_classification(self):
        cells = scan_liberty([DATA / "sram_metadata.lib"])
        name = "ot_sram_1r1w2c_16x546_m1"
        area = cells[name]["area"]
        # Deliberately constructed stat fixture, using the real macro's identity
        # and area: not represented as an additional synthesis receipt.
        stat = parse_stat(f"=== top ===\n 2 {2*area} cells\n 2 {2*area} {name}\n"
                          f" Chip area for module '\\top': {2*area}\n", "top")
        result = summarize_stat(stat, cells)
        self.assertEqual(result["macro_count"], 2)
        self.assertEqual(result["combinational_cell_count"], 0)
        self.assertEqual(result["unmapped_cell_count"], 0)

    def test_actual_sram_output_retains_unresolved_macros(self):
        stat = parse_stat((DATA / "qwen_sram_pair.txt").read_text(), "ot_qwen_hbm_code_pair_context")
        result = summarize_stat(stat, self.cells)
        self.assertEqual(result["cell_count"], 28343)
        self.assertEqual(result["unmapped_cell_count"], 20)
        self.assertEqual(result["macro_count"], 0)
        self.assertIsNone(result["cell_area_um2"])
        self.assertEqual(len(result["unknown_area_cell_types"]), 2)

    def test_actual_sram_output_with_explicit_macro_liberty(self):
        stat = parse_stat((DATA / "qwen_sram_pair.txt").read_text())
        cells = self.cells | scan_liberty([DATA / "sram_pair_metadata.lib"])
        result = summarize_stat(stat, cells)
        self.assertEqual(result["cell_count"], 28343)
        self.assertEqual(result["macro_count"], 20)
        self.assertEqual(result["unmapped_cell_count"], 0)
        self.assertGreater(result["cell_area_um2"], stat["chip_area_um2"])

    def test_liberty_area_with_and_without_semicolon(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cells.lib"
            path.write_text('library (test) {\n cell (BUF) {\n area : 0.0729\n }\n'
                            ' cell (DFF) {\n area : 0.3;\n ff (IQ, IQN) {}\n }\n}\n')
            cells = scan_liberty([path])
            self.assertEqual(cells["BUF"]["area"], 0.0729)
            self.assertEqual(cells["DFF"]["area"], 0.3)
            self.assertTrue(cells["DFF"]["sequential"])


if __name__ == "__main__":
    unittest.main()
