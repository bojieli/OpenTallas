"""DIE-QC-97 11-09: plan budgets.cland_strip_rows(_types) -> OT_CLAND_STRIP_ROWS (sle_fw_v2__cl69f5e854 GRT-0116:
x_ctl_i / cws0_i ring_ff column strips at rows 1 = 100 % FIRM at the N band edge, 3 overflow edges in that row)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys as GP  # noqa: E402
import schema as S  # noqa: E402


class StripRows(unittest.TestCase):
    def test_absent_is_unchanged(self):
        self.assertIsNone(GP._cland_strip_rows({}, "sle_fw_v2__cl69f5e854"))
        self.assertIsNone(GP._cland_strip_rows({"cland_strip_rows": 1}, "t"))

    def test_type_then_base_then_plan_wide(self):
        b = {"cland_strip_rows_types": {"sle_fw_v2__cl69f5e854": 2, "sle_hc1": 3}, "cland_strip_rows": 4}
        self.assertEqual(GP._cland_strip_rows(b, "sle_fw_v2__cl69f5e854"), 2)
        self.assertEqual(GP._cland_strip_rows(b, "sle_hc1__cl22c1ff36"), 3)
        self.assertEqual(GP._cland_strip_rows(b, "other"), 4)
        self.assertIsNone(GP._cland_strip_rows({"cland_strip_rows_types": {"a": 2}}, "b"))

    def test_type_entry_of_1_opts_out_of_plan_wide(self):
        b = {"cland_strip_rows_types": {"keep": 1}, "cland_strip_rows": 2}
        self.assertIsNone(GP._cland_strip_rows(b, "keep"))

    def test_schema_declares_the_knobs(self):
        props = S.SCHEMA["properties"]["budgets"]["properties"]
        self.assertEqual(props["cland_strip_rows"]["minimum"], 1)
        self.assertEqual(props["cland_strip_rows_types"]["additionalProperties"]["minimum"], 1)


if __name__ == "__main__":
    unittest.main()
