"""col ROM-field pipes priced (TOKEN-1121-R3): OT_COLROM=1 adds the cfg ROM-input stage to every op span and enforces the 13-edge go guard."""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent))
import xs_field_calendar as F


class ColromTest(unittest.TestCase):
    def test_record_priced_only_when_enabled_and_guard_checked(self):
        with patch.dict(os.environ, {'OT_COLROM': '0'}):
            self.assertFalse(F.colrom_on())
        with patch.dict(os.environ, {'OT_COLROM': '1'}):
            self.assertTrue(F.colrom_on())
        r = F.colrom_record(127, F.CFG_LEAD, 8)
        self.assertEqual((r['input_stage_edges'], r['go_guard_edges']), (1, 13))
        self.assertEqual(r['go_to_next_cfg_go_edges'], 127 - F.CFG_LEAD)
        self.assertTrue(r['guard_pass'])

    def test_guard_fails_when_cfg_go_follows_go_too_soon(self):
        self.assertFalse(F.colrom_record(60, 52, 4)['guard_pass'])      # 8 < 13
        self.assertTrue(F.colrom_record(65, 52, 4)['guard_pass'])       # 13
        self.assertTrue(F.colrom_record(10, 52, 1)['guard_pass'])       # single phase: no next cfg_go

    def test_static_check_names_guard(self):
        import inspect
        src = inspect.getsource(F.static_checks)
        self.assertIn('colrom_go_to_next_cfg_go_ge_guard', src)


if __name__ == '__main__':
    unittest.main()
