"""Preserve calibration behavior when the later TT overlay replaces corner code."""
import unittest
import os
import sys
import types
import textwrap
from unittest.mock import patch
import tt_overlay as overlay
import hold_corners_patch as hold


class CalibrationOverlayTests(unittest.TestCase):
    def fixture(self, segment):
        return "ORFS_CORNER_MACRO_TAG = {}\nORFS_LIB_CORNERS = {}\n" + overlay.PARSE_ANCHOR + segment + overlay.RHC_ANCHOR

    def test_hold_then_tt_keeps_cts_only(self):
        original = self.fixture(hold.CAL_CODE + overlay.CORNER_CODE)
        result, _, ok = overlay.ensure_corner(original)
        self.assertTrue(ok)
        self.assertIn('SKIP_CTS_REPAIR_TIMING=1', result)
        self.assertEqual(result.count('if os.environ.get("OT_CAL_CTS_ONLY", "") == "1":'), 1)

    def test_tt_then_hold_does_not_duplicate_cts_only(self):
        result, _, ok = overlay.ensure_corner(self.fixture(overlay.CORNER_CODE))
        self.assertTrue(ok)
        self.assertIn('OT_CAL_CTS_ONLY', result)
        self.assertEqual(result.count('SKIP_CTS_REPAIR_TIMING=1'), 2)

    def test_final_overlay_is_idempotent(self):
        result, _, ok = overlay.ensure_corner(self.fixture(overlay.CORNER_CODE))
        second, _, ok2 = overlay.ensure_corner(result)
        self.assertTrue(ok and ok2)
        self.assertEqual(second, result)

    def test_calibration_sets_skip_in_actual_driver_arguments(self):
        args = types.SimpleNamespace(orfs_var=["PDN_TCL=original"])
        with patch.dict(os.environ, {"OT_CAL_CTS_ONLY": "1"}):
            exec(textwrap.dedent(overlay.CALIBRATION_CODE), dict(os=os, sys=sys, args=args))
        self.assertEqual(args.orfs_var, ["PDN_TCL=original", "SKIP_CTS_REPAIR_TIMING=1"])

    def test_route_arguments_remain_unchanged(self):
        args = types.SimpleNamespace(orfs_var=["HOLD_SLACK_MARGIN=0.05"])
        with patch.dict(os.environ, {"OT_CAL_CTS_ONLY": ""}):
            exec(textwrap.dedent(overlay.CALIBRATION_CODE), dict(os=os, sys=sys, args=args))
        self.assertEqual(args.orfs_var, ["HOLD_SLACK_MARGIN=0.05"])


if __name__ == '__main__':
    unittest.main()
