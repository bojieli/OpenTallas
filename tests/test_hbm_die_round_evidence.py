import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location(
    'hbm_die_round_evidence', Path(__file__).resolve().parents[1] / 'tools/hbm_die_round_evidence.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DieEvidenceTests(unittest.TestCase):
    def test_pin_failure_is_retained_despite_legal_placement(self):
        record = MODULE.parse_log('OT_LEGAL instances=504 overlaps=0 outside=0\n'
                                  'OT_MACRO_TRACK_ASSERT PASS label=hbmaccdie\n'
                                  '[ERROR DRT-0073] No access point for w143/a[2063].\n'
                                  'OT_PA FAIL DRT-0073\n')
        self.assertEqual(record['placement']['overlaps'], 0)
        self.assertEqual(record['on_track'], 'PASS')
        self.assertEqual(record['pin_access'], 'FAIL')
        self.assertEqual(len(record['pin_access_errors']), 1)

    def test_no_path_is_not_zero_slack_and_units_are_explicit(self):
        record = MODULE.parse_log('OT_STA_VIEW station insts=16 setup_u210=NA hold=NA\n'
                                  'OT_STA_VIEW tile insts=64 setup_u210=-2.048526 hold=0.092668\n'
                                  'OT_STA_DONE timed_insts=80\n')
        self.assertEqual(record['sta']['views_without_numeric_result'], 1)
        self.assertIsNone(record['sta']['views'][0]['setup_u210_ps'])
        self.assertEqual(record['sta']['views'][1]['setup_u210_ps'], -2048.526)
        self.assertEqual(record['sta']['views'][1]['hold_ps'], 92.668)
        self.assertEqual(record['sta_declared_timed_instances'], 80)


if __name__ == '__main__':
    unittest.main()
